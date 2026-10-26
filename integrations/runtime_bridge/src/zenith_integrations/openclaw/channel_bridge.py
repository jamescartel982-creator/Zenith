"""Exactly approved report delivery via native send, never chat.send or a model prompt."""
import hashlib
import json
import re

from ..shared.native_http import NativeRefused, UnknownExecution


class ChannelBridge:
    def __init__(self,client,ledger,profile_id,verify_owner):
        self.client,self.ledger,self.profile_id,self.verify_owner=client,ledger,profile_id,verify_owner

    async def deliver(self,actor,grant_id,text,channel,recipient,idempotency_key):
        if not isinstance(text,str) or not 1<=len(text.encode())<=64000:
            raise ValueError('An explicit bounded text report is required')
        if not re.fullmatch(r'[a-zA-Z0-9_-]{1,64}',channel) or not re.fullmatch(r'[a-zA-Z0-9+@.:/_-]{1,256}',recipient) or not re.fullmatch(r'[a-zA-Z0-9_-]{8,128}',idempotency_key):
            raise ValueError('Use an explicit configured channel, canonical recipient and stable key')
        digest=hashlib.sha256(text.encode()).hexdigest()
        scope={'runtime':'openclaw','operation':'deliver','channel':channel,'recipient':recipient,'report_sha256':digest}
        current=await self.verify_owner()
        if current!=actor or not self.ledger.allows(actor,grant_id,'reports.deliver',scope) or self.ledger.stopped():
            raise NativeRefused('exact_owner_report_approval_required')
        if not self.client.hello:
            await self.client.connect()
        # Bind replay to this physical native profile/device rather than silently
        # sending again after credentials or target infrastructure change.
        # Connection ids change on reconnect; bind the actual device and
        # credential generation as well as the configured native profile.
        payload={'report_sha256':digest,'channel':channel,'recipient':recipient,'native_profile':self.profile_id,
                 'gateway_origin':self.client.url,'grant_id':grant_id,
                 'native_device_id':self.client.device_id,'credential_generation':self.client.credential_fingerprint}
        key='delivery_'+hashlib.sha256((self.profile_id+'\0'+idempotency_key).encode()).hexdigest()
        row,admitted=self.ledger.admit(actor,key,{'runtime':'openclaw','operation':'report-delivery','payload':payload})
        if not admitted:
            if row['status']=='succeeded':
                return json.loads(row['result'])
            raise UnknownExecution('This report already has an execution owner; reconcile its native receipt')
        if not self.ledger.transition(row['id'],{'queued'},'running'):
            raise NativeRefused('delivery_admission_revoked')
        try:
            current=await self.verify_owner()
            if current!=actor or not self.ledger.allows(actor,grant_id,'reports.deliver',scope) or self.ledger.stopped():
                self.ledger.transition(row['id'],{'running'},'cancelled',error='approval_revoked')
                raise NativeRefused('report_approval_revoked')
            ack=await self.client._rpc('send',{'to':recipient,'message':text,'channel':channel,'idempotencyKey':row['id']})
            if not isinstance(ack,dict) or ack.get('channel')!=channel or ack.get('runId')!=row['id'] or not isinstance(ack.get('messageId'),str) or not ack['messageId']:
                raise UnknownExecution('Native delivery receipt is incomplete; do not resend')
            result={'runtime':'openclaw','report_sha256':digest,'channel':channel,'recipient':recipient,
                    'native_message_id':ack['messageId'],'native_run_id':ack['runId'],'status':'native_acknowledged'}
            observed=self.ledger.get(row['id'],actor)
            result['cancellation_requested']=observed['status']!='running'
            # A real platform receipt is evidence of delivery, even if a late
            # local cancellation raced the committed external action.
            self.ledger.transition(row['id'],{'running','cancel_requested','cancelled','interrupted'},'succeeded',result=result)
            return result
        except NativeRefused:
            self.ledger.transition(row['id'],{'running'},'failed',error='native_delivery_refused')
            raise
        except BaseException:
            self.ledger.transition(row['id'],{'running'},'interrupted',error='native_delivery_reconciliation_required')
            raise
