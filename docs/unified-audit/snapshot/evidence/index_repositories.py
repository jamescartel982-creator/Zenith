"""Read-only inventories: hashes/AST anchors; never imports audited project code."""
import ast,collections,csv,gzip,hashlib,json,re,subprocess,tomllib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];E=ROOT/'evidence'
REPOS={
'openclaw':Path('/workspace/openclaw-review-20261025/openclaw'),
'hermes':ROOT/'hermes-agent',
'zenith-main':ROOT/'zenith-main',
'zenith-pr19':Path('/workspace/zenith-platform'),
}
registrations=[];manifests=[];skills=[];docs=[];legals=[];packages=[];summaries={}
for key,root in REPOS.items():
 names=subprocess.check_output(['git','-C',str(root),'ls-files','-z']).decode().split('\0')[:-1]
 sha=subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD'],text=True).strip()
 summary={'commit':sha,'branch':subprocess.check_output(['git','-C',str(root),'branch','--show-current'],text=True).strip() or 'detached','tracked_files':len(names),'top_level_counts':dict(collections.Counter(n.split('/')[0] for n in names)),'extensions':dict(collections.Counter(Path(n).suffix for n in names)),'python_modules':0,'python_parse_failures':[],'test_named_paths':0,'plugin_manifests':0,'skills':0,'documents':0,'index_scope':'Whole tracked tree hashed. Python AST on host 3.12; TS/JS imports/exports regex, not a complete semantic call graph. No project code imported.'}
 with gzip.open(E/f'{key}-source-index.jsonl.gz','wt',encoding='utf-8') as out:
  for name in names:
   path=root/name
   if path.is_symlink():
    row={'repository':key,'commit':sha,'path':name,'symlink_target':str(path.readlink())}
    out.write(json.dumps(row)+'\n');continue
   data=path.read_bytes();row={'repository':key,'commit':sha,'path':name,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
   text=None
   if path.suffix in {'.py','.ts','.tsx','.js','.mjs','.mts','.md','.mdx','.yaml','.yml','.toml','.json'} or path.name in {'LICENSE','NOTICE','COPYING','COPYRIGHT'}:
    text=data.decode('utf-8',errors='replace')
   if re.search(r'test|spec|suite',path.name,re.I):summary['test_named_paths']+=1
   if text is not None and path.suffix=='.py':
    summary['python_modules']+=1
    try:
     tree=ast.parse(text,filename=name)
     row['imports']=[{'line':n.lineno,'text':ast.unparse(n)} for n in tree.body if isinstance(n,(ast.Import,ast.ImportFrom))]
     row['symbols']=[{'name':n.name,'line':n.lineno,'kind':type(n).__name__} for n in tree.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef))]
     if key=='hermes':
      constants={n.targets[0].id:n.value for n in tree.body if isinstance(n,ast.Assign) and len(n.targets)==1 and isinstance(n.targets[0],ast.Name)}
      for node in ast.walk(tree):
       if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute) and node.func.attr=='register':
        keywords={k.arg:k.value for k in node.keywords if k.arg}
        if not any(k in keywords for k in ('name','schema','handler','toolset')):continue
        entry={'repository':key,'path':name,'line':node.lineno,'call':ast.unparse(node.func),'declared_name':None,'toolset':None,'handler':None,'schema_reference':None,'dynamic':False}
        for prop in ('name','toolset','handler'):
         value=keywords.get(prop)
         if isinstance(value,ast.Constant):entry['declared_name' if prop=='name' else prop]=value.value
         elif value is not None:entry['declared_name' if prop=='name' else prop]=ast.unparse(value);entry['dynamic']=True
        schema=keywords.get('schema')
        if schema is not None:
         entry['schema_reference']=ast.unparse(schema)
         if isinstance(schema,ast.Name):schema=constants.get(schema.id,schema)
         try:
          literal=ast.literal_eval(schema)
          if isinstance(literal,dict):
           entry['schema_name']=literal.get('name') or literal.get('function',{}).get('name')
           entry['schema_description']=literal.get('description') or literal.get('function',{}).get('description')
         except (ValueError,TypeError,SyntaxError):pass
        registrations.append(entry)
    except SyntaxError as ex:
     row['parse_failure']={'line':ex.lineno,'message':ex.msg};summary['python_parse_failures'].append({'path':name,**row['parse_failure']})
     row['regex_symbols']=[{'name':m.group(1),'line':text.count('\n',0,m.start())+1} for m in re.finditer(r'^(?:async\s+)?(?:def|class)\s+(\w+)',text,re.M)]
   elif text is not None and path.suffix in {'.ts','.tsx','.js','.mjs','.mts'}:
    row['static_imports']=sorted(set(re.findall(r'(?:from\s+|import\s*\(\s*|import\s+)[\'\"]([^\'\"\n]+)[\'\"]',text)))
    row['export_symbols']=[{'name':m.group(1),'line':text.count('\n',0,m.start())+1} for m in re.finditer(r'export\s+(?:async\s+)?(?:function|class|const|type|interface)\s+(\w+)',text)]
   if text is not None and path.name in {'plugin.yaml','plugin.yml','openclaw.plugin.json'}:
    entry={'repository':key,'path':name,'sha256':row['sha256'],'manifest':None}
    try:
     if path.suffix=='.json':entry['manifest']=json.loads(text)
     else:
      import yaml
      entry['manifest']=yaml.safe_load(text)
    except Exception as ex:entry['parse_error']=type(ex).__name__
    manifests.append(entry);summary['plugin_manifests']+=1
   if text is not None and path.name=='SKILL.md':
    fields={}
    if text.startswith('---'):
     header=text.split('---',2)[1]
     for m in re.finditer(r'^([\w-]+):\s*(.*)$',header,re.M):fields[m.group(1)]=m.group(2).strip()
    skills.append({'repository':key,'path':name,'sha256':row['sha256'],'frontmatter_excerpt':fields,'semantics':'Prompt/resource package declaration, not an automatically verified executable tool.'});summary['skills']+=1
   if text is not None and path.suffix in {'.md','.mdx'}:
    if (key=='hermes' and (name.startswith('website/docs/') or name=='README.md')) or (key=='openclaw' and (name.startswith('docs/') or name=='README.md')):
     headings=[{'line':i,'title':line.lstrip('#').strip()} for i,line in enumerate(text.splitlines(),1) if re.match(r'^#{1,4}\s',line)]
     docs.append({'repository':key,'path':name,'sha256':row['sha256'],'headings':headings,'evidence':'documentation; headings are coverage anchors, not independent capability verification'});summary['documents']+=1
   if path.suffix.lower() in {'','.md','.txt','.license'} and re.search(r'(^|[-_.])(LICENSE|LICENCE|NOTICES?|COPYING|COPYRIGHT)([-_.]|$)',path.name,re.I):
    legals.append({'repository':key,'path':name,'sha256':row['sha256'],'opening':data.decode('utf8',errors='replace').splitlines()[:7]})
   if path.name=='package.json':
    try:
     p=json.loads(text);packages.append({'repository':key,'path':name,**{k:p.get(k) for k in ('name','version','license','engines','packageManager','dependencies','optionalDependencies','devDependencies','scripts')}})
    except (ValueError,TypeError):pass
   if path.name=='pyproject.toml':
    try:
     p=tomllib.loads(text);packages.append({'repository':key,'path':name,'project':p.get('project',{}),'build-system':p.get('build-system',{}),'tool-uv':p.get('tool',{}).get('uv',{})})
    except (ValueError,TypeError):pass
   out.write(json.dumps(row,ensure_ascii=False)+'\n')
 summaries[key]=summary
 print(key,sha,len(names),'Python',summary['python_modules'],'parse failures',len(summary['python_parse_failures']),'manifests',summary['plugin_manifests'],'skills',summary['skills'],'docs',summary['documents'],flush=True)
for name,value in [('repositories',summaries),('tool-registrations',registrations),('plugin-manifests',manifests),('skill-packages',skills),('documentation-index',docs),('license-inventory',legals),('dependency-declarations',packages)]:
 (E/f'{name}.json').write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
