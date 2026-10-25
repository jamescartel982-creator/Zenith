"""Explicit owner/MFA capability grants, scoped diagnostics, and emergency stop."""
import hashlib
import ipaddress
import json
import socket
import ssl
import time

CAPABILITIES={'calculator':'Bounded exact arithmetic offline','sha256':'Digest pasted text offline','decode-base64':'Decode pasted Base64 offline','code-audit':'Review pasted source offline','inspect-url':'Inspect URL components offline',
              'verify-python':'Test a bounded numeric Python subset in an isolated interpreter process',
              'tcp-connect':'One TCP connectivity check to an approved host and port',
              'tls-certificate':'Verify one TLS peer certificate in approved network scope'}


def scope_definition(scope,network=False):
    if not isinstance(scope,dict):raise ValueError('Scope must be an object')
    if not network:
        if scope!={'kind':'offline'}:raise ValueError('Pasted-data diagnostics require offline scope')
        return scope
    if set(scope)!={'kind','cidrs','ports','authorization_reference'} or scope['kind']!='network':
        raise ValueError('Network grants require CIDRs, ports, and an authorization reference')
    if not isinstance(scope['authorization_reference'],str) or not 1<=len(scope['authorization_reference'].strip())<=200:
        raise ValueError('Record the written authorization reference')
    if not isinstance(scope['cidrs'],list) or not 1<=len(scope['cidrs'])<=8:
        raise ValueError('Provide bounded, explicit target networks')
    networks=[]
    for value in scope['cidrs']:
        if not isinstance(value,str) or len(value)>80:raise ValueError('Invalid CIDR scope')
        net=ipaddress.ip_network(value,strict=True)
        if net.prefixlen < (24 if net.version==4 else 64):raise ValueError('Target ranges must be narrow: /24 or smaller, or /64 or smaller')
        networks.append(str(net))
    ports=scope['ports']
    if not isinstance(ports,list) or not 1<=len(ports)<=16 or any(type(p)!=int or not 1<=p<=65535 for p in ports):
        raise ValueError('List explicit authorized ports')
    return {**scope,'cidrs':networks,'ports':sorted(set(ports))}


def authorized_addresses(host,port,scope):
    if not isinstance(host,str) or len(host)>253 or not host or any(c.isspace() for c in host) or '%' in host:
        raise ValueError('Use a literal IP without credentials, a URL, or a zone identifier')
    if type(port)!=int or port not in scope['ports']:raise PermissionError('Port is outside the active grant')
    networks=[ipaddress.ip_network(n) for n in scope['cidrs']]
    try:ip=ipaddress.ip_address(host)
    except ValueError as exc:raise ValueError('Use an explicitly approved literal IP; hostname resolution is not enabled') from exc
    if ip.version==6 and ip.ipv4_mapped:ip=ip.ipv4_mapped
    if ip.is_unspecified or ip.is_multicast or ip.is_link_local or not any(ip in net for net in networks if ip.version==net.version):
        raise PermissionError('Target address is outside the approved scope')
    return [str(ip)]



class ExecutionControls:
    def __init__(self,store,admin):
        self.store,self.admin=store,admin
        with store.connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS execution_grants (token_hash TEXT NOT NULL, user_id TEXT NOT NULL, capability TEXT NOT NULL, scope TEXT NOT NULL, expires REAL NOT NULL, PRIMARY KEY(token_hash,capability))')
            db.execute('CREATE TABLE IF NOT EXISTS execution_state (singleton INTEGER PRIMARY KEY CHECK(singleton=1), stopped INTEGER NOT NULL)')
            db.execute('INSERT OR IGNORE INTO execution_state VALUES (1,0)')
            db.execute('CREATE TABLE IF NOT EXISTS execution_audit (id INTEGER PRIMARY KEY AUTOINCREMENT, created REAL NOT NULL, user_id TEXT NOT NULL, capability TEXT NOT NULL, event TEXT NOT NULL, target TEXT NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS agent_tasks (id TEXT PRIMARY KEY,user_id TEXT NOT NULL, created REAL NOT NULL,status TEXT NOT NULL,steps TEXT NOT NULL,results TEXT NOT NULL)')

    def _owner(self,user_id,token,require_mfa=True):
        state=self.admin.status(user_id,token)
        if not state['eligible'] or not state['elevated']:raise PermissionError('Owner login and current elevation required')
        if require_mfa and (not state['mfa_configured'] or not state['mfa_verified']):
            raise PermissionError('Configure and verify owner multifactor authentication first')
        return state

    def _audit(self,user_id,capability,event,target=''):
        with self.store.connect() as db:
            db.execute('INSERT INTO execution_audit(created,user_id,capability,event,target) VALUES (?,?,?,?,?)',
                       (time.time(),user_id,capability,event,target[:300]))

    def status(self,user_id,token):
        state=self.admin.status(user_id,token)
        with self.store.connect() as db:
            stopped=bool(db.execute('SELECT stopped FROM execution_state WHERE singleton=1').fetchone()['stopped'])
            grants=[dict(r) for r in db.execute('SELECT capability,scope,expires FROM execution_grants WHERE token_hash=? AND user_id=? AND expires>?',
                (hashlib.sha256(token.encode()).hexdigest(),user_id,time.time()))] if state['eligible'] and state['elevated'] and state['mfa_verified'] else []
        return {'stopped':stopped,'capabilities':CAPABILITIES,'active_grants':[{**g,'scope':json.loads(g['scope'])} for g in grants],
                'mfa_required':True,'network_tools_enabled_by_default':False}

    def grant(self,user_id,token,capability,scope,seconds=300):
        state=self._owner(user_id,token)
        if capability not in CAPABILITIES or type(seconds)!=int or not 1<=seconds<=900:
            raise ValueError('Unknown capability or invalid expiry')
        scope=scope_definition(scope,capability in {'tcp-connect','tls-certificate'})
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            if db.execute('SELECT stopped FROM execution_state WHERE singleton=1').fetchone()['stopped']:
                raise PermissionError('Emergency shutdown is active; explicitly resume before granting capabilities')
            db.execute('INSERT OR REPLACE INTO execution_grants VALUES (?,?,?,?,?)',
                (hashlib.sha256(token.encode()).hexdigest(),user_id,capability,json.dumps(scope),min(time.time()+seconds,state['expires_at'])))
        self._audit(user_id,capability,'grant')
        return self.status(user_id,token)

    def revoke(self,user_id,token,capability=None):
        self._owner(user_id,token,require_mfa=False)
        with self.store.connect() as db:
            db.execute('DELETE FROM execution_grants WHERE token_hash=?'+(' AND capability=?' if capability else ''),
                (hashlib.sha256(token.encode()).hexdigest(),capability) if capability else (hashlib.sha256(token.encode()).hexdigest(),))
        self._audit(user_id,capability or '*','revoke')

    def emergency(self,user_id,token,stopped=True):
        self._owner(user_id,token,require_mfa=not stopped)
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            db.execute('UPDATE execution_state SET stopped=? WHERE singleton=1',(int(stopped),))
            db.execute('DELETE FROM execution_grants')
            if stopped:db.execute('UPDATE admin_elevations SET devil=0')
        self._audit(user_id,'*','emergency-stop' if stopped else 'explicit-resume')
        return self.status(user_id,token)

    def require(self,user_id,token,capability):
        self._owner(user_id,token)
        status=self.status(user_id,token)
        if status['stopped']:raise PermissionError('Emergency shutdown is active')
        grant=next((g for g in status['active_grants'] if g['capability']==capability),None)
        if grant is None:raise PermissionError('Explicit capability activation is required')
        return grant['scope']

    def execute(self,user_id,token,capability,arguments):
        target=''
        try:
            scope=self.require(user_id,token,capability)
            if not isinstance(arguments,dict):raise ValueError('Tool arguments must be an object')
            if capability in {'calculator','sha256','decode-base64','code-audit','inspect-url'}:
                if set(arguments)!={'text'} or not isinstance(arguments['text'],str) or len(arguments['text'])>12000:
                    raise ValueError('Supply bounded text only')
                from .tools import run_tool
                self.require(user_id,token,capability)
                result=run_tool(capability,arguments['text'])
            elif capability == 'verify-python':
                from .verification import run_restricted_tests
                self.require(user_id,token,capability)
                result=run_restricted_tests(arguments)
            elif capability in {'tcp-connect','tls-certificate'}:
                if set(arguments)!={'host','port'}:raise ValueError('Supply only host and port')
                host,port=arguments['host'],arguments['port']
                addresses=authorized_addresses(host,port,scope)
                target=str(host)+':'+str(port)
                # Connect to the validated numeric address; never resolve again or follow redirects.
                self.require(user_id,token,capability)
                with socket.create_connection((addresses[0],port),timeout=3) as connection:
                    if capability=='tls-certificate':
                        with ssl.create_default_context().wrap_socket(connection,server_hostname=host) as secure:
                            cert=secure.getpeercert()
                            result={'verified':True,'issuer':cert.get('issuer'),'not_after':cert.get('notAfter')}
                    else:result={'reachable':True,'address':addresses[0],'port':port}
            else:raise ValueError('Capability is not implemented')
            # Revocation during a bounded I/O step discards the result and stops a plan.
            self.require(user_id,token,capability)
            self._audit(user_id,capability,'completed',target)
            return result
        except (ValueError,PermissionError,OSError) as exc:
            self._audit(user_id,capability,'denied' if isinstance(exc,PermissionError) else 'failed',target)
            raise

    def run_plan(self,user_id,token,steps):
        from uuid import uuid4
        self._owner(user_id,token)
        if not isinstance(steps,list) or not 1<=len(steps)<=8:raise ValueError('A plan needs one to eight explicit tool steps')
        for step in steps:
            if not isinstance(step,dict) or set(step)!={'tool','arguments'} or step['tool'] not in CAPABILITIES:
                raise ValueError('Every plan step must use a registered capability and arguments')
        identifier=str(uuid4());results=[];started=time.monotonic()
        with self.store.connect() as db:
            # Store the approved plan structure, not pasted source or secret-bearing inputs.
            db.execute('INSERT INTO agent_tasks VALUES (?,?,?,?,?,?)',(identifier,user_id,time.time(),'running',json.dumps([s['tool'] for s in steps]),'[]'))
        status='failed'
        try:
            for step in steps:
                if time.monotonic()-started>45:raise ValueError('Plan time budget exceeded')
                value=self.execute(user_id,token,step['tool'],step['arguments'])
                results.append(value)
            status='completed'
            return {'task_id':identifier,'results':results,'status':status}
        finally:
            with self.store.connect() as db:
                db.execute('UPDATE agent_tasks SET status=?,results=? WHERE id=?',
                    (status,json.dumps({'completed_steps':len(results)}),identifier))
