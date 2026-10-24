"""Prepare a licensed authored primer plus verified historical training replay.

This bounded technical primer is not a comprehensive expert-training corpus.
"""
import argparse
import json
from pathlib import Path
from agent.checkpoints import digest
from agent.curriculum import prepare

LESSONS = {
 'ai':[
 ('backprop','What does backpropagation compute?','Backpropagation applies the chain rule to compute gradients of a loss with respect to parameters. An optimizer uses those gradients to update the parameters.'),
 ('attention','Explain causal self-attention.','Causal self-attention lets each token attend to itself and earlier tokens. It masks future tokens to prevent access to the answer during next-token training.'),
 ('supervision','Distinguish supervised learning from reinforcement learning.','Supervised learning fits labeled examples. Reinforcement learning optimizes decisions using rewards from interactions; its evaluation must account for exploration and the environment.'),
 ('overfitting','Training loss falls while validation loss rises. What should I investigate?','Investigate overfitting, split leakage, distribution differences, and preprocessing. Compare a held-out baseline; consider early stopping, regularization, and more representative data.'),
 ('vision','How does a convolutional layer process an image?','A convolutional layer applies shared filters across local spatial neighborhoods, producing feature maps. It can learn edges and more complex visual features across layers.'),
 ('nlp','Why must a model keep its tokenizer compatible during continued training?','Token IDs index existing embedding rows. Changing the ID mapping changes their meaning. Verify vocabulary, special tokens, and chat-template compatibility before loading or exporting.'),
 ('agents','What separates a language model from an agent harness?','The model predicts outputs. The harness supplies context, validates structured actions, enforces permissions, executes allowed tools, and records results.'),
 ('evaluation','How should a new adapter be compared with its parent?','Use the same held-out tasks and settings. Measure improvements, retained capabilities, failures by slice, and latency. Preserve the parent and require review before promotion.'),
 ('statistics','Why is a lower training loss insufficient evidence of improvement?','Training loss measures fit to seen examples. It does not establish generalization, retained capability, correct reasoning, or safe tool use; held-out evaluations are required.'),
 ('representation','What is an embedding?','An embedding maps a discrete item such as a token to a learned numeric vector. The vector is a representation, rather than a verified factual database.'),
 ('transfer','How does continued pretraining differ from instruction fine-tuning?','Continued pretraining typically predicts tokens in domain text. Instruction fine-tuning trains responses to instructions, often masking the prompt from the loss.'),
 ('calibration','What is probability calibration?','Calibration compares predicted probabilities with observed correctness frequencies. A confident-sounding response alone is not calibrated uncertainty.')],
 'programming':[
 ('python','In Python, remove duplicates while preserving input order.','For hashable items, use list(dict.fromkeys(items)). For unhashable objects, define an equality or key-based strategy and test its behavior.'),
 ('c','How can C code prevent a buffer overwrite when copying bytes?','Track destination capacity and source length, reject oversized copies, and account for the null terminator for strings. Validate lengths before copying and test boundary cases.'),
 ('cpp','What is RAII in C++?','Resource Acquisition Is Initialization binds resource ownership to object lifetime. Destructors release resources; use standard containers and smart pointers for clear ownership.'),
 ('rust','Why does Rust distinguish shared and mutable references?','Shared references permit reading; a mutable reference grants exclusive access while its borrow is active. These rules prevent many data races and invalid aliasing patterns.'),
 ('java','How should Java release a resource implementing AutoCloseable?','Use try-with-resources so close runs when the block exits, including exceptional exits. Handle exceptions without silently discarding the original failure.'),
 ('javascript','How should JavaScript handle a rejected asynchronous request?','Await the promise inside try/catch or attach a rejection handler. Check HTTP status separately because fetch can resolve for an HTTP error response.'),
 ('typescript','What does TypeScript narrowing do?','Narrowing refines a value type using checks such as typeof, discriminants, and null guards. Runtime inputs still need validation because types are erased.'),
 ('go','How should a Go caller handle an error return?','Check err before using the returned result. Add useful context when propagating errors and ensure owned resources are closed with appropriate defer calls.'),
 ('bash','How do Bash scripts preserve spaces in a path argument?','Quote parameter expansions, for example "$path" and "$@". Avoid eval and constructing shell commands from untrusted strings.'),
 ('sql','How should an application prevent SQL injection?','Use parameterized queries for values and validate identifiers separately. Do not concatenate user input into SQL; also restrict database permissions.'),
 ('architecture','How can a service isolate persistence from business logic?','Define an explicit repository interface, keep transaction boundaries clear, and inject an implementation. Test behavior and failure recovery at the boundary.'),
 ('debugging','What is a disciplined debugging workflow?','Reproduce the failure, minimize the case, inspect evidence, form a hypothesis, change one relevant cause, and verify both the failing case and important regressions.'),
 ('reverse-engineering','How can I inspect the behavior of my own compiled application safely?','Work from a copy in an isolated lab. Inspect file metadata, symbols, and disassembly; record observations and validate hypotheses against known inputs without touching third-party targets.'),
 ('api','How should an API validate a tool execution request?','Authenticate the caller, validate the schema, enforce a server-side capability and target scope, apply resource limits, and record the outcome. Model-generated claims do not grant permission.'),
 ('systems','What must code handle when reading from a socket?','Handle partial reads, EOF, timeouts, framing, size limits, and invalid encoding. One read call does not necessarily return one complete application message.')],
 'infrastructure':[
 ('linux','How can an operator diagnose a Linux service that will not start?','Inspect its status and recent service logs, validate configuration, check ownership and permissions, inspect port conflicts, and verify dependencies before restarting.'),
 ('windows','How should a Windows application isolate Python dependencies?','Create a virtual environment and invoke its Python executable or activate it in the current shell. Avoid globally upgrading dependencies used by other applications.'),
 ('docker','Why should a container run as a non-root user?','A non-root user reduces privileges available to a compromised process. Also restrict mounts, capabilities, network exposure, and secrets; non-root alone is not isolation proof.'),
 ('kubernetes','What do Kubernetes readiness and liveness probes mean?','Readiness determines whether a workload should receive traffic. Liveness detects a condition requiring restart. Configure them carefully to avoid restart loops.'),
 ('cloud','How should cloud service credentials be managed?','Prefer short-lived workload identities and least-privilege roles. Keep credentials out of source, logs, prompts, and images; rotate and audit access.'),
 ('networking','What is the difference between TCP and UDP?','TCP provides an ordered reliable byte stream with congestion control. UDP sends datagrams without built-in delivery or ordering guarantees; applications add needed reliability.'),
 ('firewall','How should a new firewall rule be introduced?','Document allowed traffic and business purpose, restrict sources and ports, test in a controlled environment, record the change, and keep a rollback path.'),
 ('vpn','Does a VPN replace application authentication?','No. A VPN controls network connectivity. Applications still require authentication, authorization, least privilege, and monitoring.'),
 ('virtualization','How is a virtual machine different from a container?','A virtual machine typically runs its own guest kernel over virtual hardware. Containers share the host kernel while isolating processes and resources.'),
 ('backups','How should backup readiness be verified?','Test restoration from independent backups, validate integrity and access controls, measure recovery time, and document responsibilities. A successful backup job alone is insufficient.'),
 ('dns','How should an application avoid DNS-based scope bypass in a network tool?','Validate approved targets, resolve and check resulting addresses immediately before use, reject out-of-scope results, and avoid unvalidated redirects or hostname changes.'),
 ('servers','Why is localhost the default for a personal AI web interface?','Localhost limits exposure to the local machine. Shared deployment requires explicit network configuration, authentication, authorization, and transport protection.')],
 'science-mathematics':[
 ('algebra','Solve 3x + 5 = 20 and verify the solution.','Subtract 5: 3x = 15. Divide by 3: x = 5. Substitution gives 3 times 5 plus 5 equals 20.'),
 ('calculus','Differentiate x cubed with respect to x.','The power rule gives d(x^3)/dx = 3x^2.'),
 ('integrals','Compute the definite integral of 2x from 0 to 3.','An antiderivative is x squared. Evaluating at the bounds gives 3 squared minus 0 squared, which is 9.'),
 ('bayes','State Bayes theorem and define its denominator.','P(A given B) = P(B given A) P(A) / P(B), when P(B) is positive. P(B) is the probability of the observed evidence.'),
 ('statistics','Why can correlation fail to establish causation?','Confounding, selection effects, and reverse causality can produce correlations. Causal claims require an appropriate design and assumptions, such as a controlled intervention.'),
 ('physics','A constant force of 6 newtons acts on a 2 kilogram mass. What acceleration follows?','Using F = ma, acceleration is 6 divided by 2 = 3 meters per second squared, assuming the net force and constant mass described.'),
 ('chemistry','What does conservation of atoms require when balancing a chemical equation?','Each element must have the same number of atoms on both sides. Change stoichiometric coefficients rather than molecular subscripts.'),
 ('biology','What is the role of DNA in a cell?','DNA stores hereditary sequence information. Gene expression uses this information to produce functional RNA and, through translation, proteins.'),
 ('complexity','What is the time complexity of binary search on a sorted random-access array?','Binary search takes O(log n) comparisons by halving the search interval. It requires sorted data and suitable access to the middle element.'),
 ('numerics','Why should floating-point results use tolerances in tests?','Many real numbers lack exact finite binary representations. Use suitable absolute and relative tolerances based on scale and numerical error; avoid arbitrary exact equality.'),
 ('research','How can a scientific experiment be made reproducible?','Record data provenance, procedures, configuration, software versions, seeds, exclusions, and analysis. Share permitted artifacts and distinguish replication from identical random outcomes.'),
 ('reasoning','A store sells three notebooks at four dollars each. What is the total before tax?','Multiply 3 by 4 to obtain 12 dollars before tax.')],
 'white-hat':[
 ('scope','What must be established before an authorized penetration test?','Written authorization must define targets, permitted methods, dates, contacts, data handling, and stop conditions. Verify scope before any execution.'),
 ('review','How should a secure code review treat a user-controlled SQL value?','Trace the input to the query sink, verify parameter binding, assess authorization and least privilege, and recommend a testable remediation.'),
 ('remediation','What belongs in a vulnerability remediation report?','Describe affected assets, evidence, impact, reproduction within authorized scope, recommended fixes, priority, and a retest plan. Exclude unnecessary sensitive data.'),
 ('audit','How does a security audit differ from exploitation?','An audit checks controls and evidence against defined requirements. It does not require exploiting systems; any active testing needs explicit authorization.')],
 'blue-hat':[
 ('soc','How should a SOC investigate a spike in failed logins?','Correlate timestamps, accounts, source addresses, device context, and successful logins. Preserve evidence, assess false positives, and follow approved containment procedures.'),
 ('response','What are core incident-response steps?','Prepare, detect and analyze, contain, eradicate, recover, and learn from the incident. Preserve evidence and coordinate decisions with authorized responders.'),
 ('monitoring','What makes a detection rule operationally useful?','Define the threat behavior, required telemetry, logic, expected benign patterns, test evidence, severity, ownership, and an investigation playbook.'),
 ('automation','How should defensive automation avoid disrupting production?','Use least privilege, bounded actions, dry-run validation, explicit approvals for disruptive steps, audit logs, and a tested emergency stop.')],
 'green-hat':[
 ('basics','What does least privilege mean?','Grant only the permissions needed for a task, for the necessary duration. Review access and remove unnecessary privileges.'),
 ('crypto','How does hashing differ from encryption?','A cryptographic hash is a one-way digest used for integrity and related purposes. Encryption uses a key to protect data and permits decryption by an authorized holder.'),
 ('ctf','How can a beginner practice security safely?','Use authorized CTFs and isolated intentionally vulnerable labs. Read rules and scope, keep experiments separate from real services, and document what was learned.')],
 'gray-hat':[
 ('disclosure','What is coordinated vulnerability disclosure?','Report a flaw privately through the authorized contact, minimize sensitive evidence, agree on remediation and disclosure timing, and avoid testing beyond permission.'),
 ('patch','How should an analyst compare a security patch?','Compare trusted source versions, identify the affected logic and threat assumptions, reproduce behavior in an isolated authorized lab, and validate the mitigation.'),
 ('lab','How should a vulnerability research lab be isolated?','Use disposable systems, restricted networking, snapshots, synthetic data, and clear authorization. Prevent connections to third-party systems.'),
 ('mitigation','How can a vulnerability be mitigated before a patch is available?','Assess exposure, restrict affected functionality or access, apply vendor-approved workarounds, monitor relevant events, and track the temporary control until patch validation.')],
 'red-hat':[
 ('emulation','What distinguishes authorized adversary emulation from an intrusion?','Emulation follows a written engagement plan, approved targets and techniques, safety controls, and stop conditions, with defensive learning as its purpose.'),
 ('purple','What is purple-team collaboration?','Offensive and defensive specialists collaborate on authorized simulations, compare telemetry with expected behavior, identify detection gaps, and retest improvements.'),
 ('tactics','How should a threat tactic be mapped to a defensive test?','State the behavior and hypothesis, choose a safe scoped simulation, identify expected telemetry, define success criteria, and review the observed detection result.'),
 ('stop','When must an authorized simulation stop?','Stop when authorization expires, scope changes, a stop condition triggers, unexpected impact appears, or the authorized owner revokes permission.')],
 'black-hat-defense':[
 ('malware','How should suspicious malware be examined defensively?','Preserve the original, compute hashes, inspect static metadata, and analyze copies only in an isolated lab. Avoid running unknown code on production systems.'),
 ('ransomware','What should responders prioritize during suspected ransomware activity?','Follow the incident plan: isolate affected systems through authorized controls, preserve evidence, assess scope, protect backups, and coordinate recovery with responders.'),
 ('forensics','Why does digital forensics require a chain of custody?','A chain of custody records who handled evidence, when, how it was acquired, and how integrity was checked. Analyze verified copies and preserve originals.'),
 ('intrusion','How can malicious persistence be investigated safely?','Review authorized endpoint telemetry, scheduled tasks, service changes, and startup entries. Correlate evidence and preserve artifacts before approved remediation.')],
 'reasoning-communication':[
 ('uncertainty','What should an assistant do when evidence is insufficient?','State the uncertainty, identify the missing evidence, and avoid inventing facts. Ask a focused question or suggest a way to verify the claim.'),
 ('planning','How should a complex software task be decomposed?','Define the desired behavior and constraints, identify dependencies, split work into verifiable steps, execute bounded changes, and check the result against acceptance criteria.'),
 ('counterexample','How can a proposed general rule be tested?','State its assumptions, check edge cases, and search for a counterexample. One valid counterexample disproves a universal claim.'),
 ('writing','How should a technical explanation be adapted to a beginner?','Lead with the result, define necessary terms, use a small concrete example, and state limitations without unnecessary jargon.'),
 ('synthesis','How should conflicting research sources be synthesized?','Compare definitions, dates, methods, and evidence quality. Explain unresolved disagreements and cite the relevant sources rather than silently selecting a convenient answer.'),
 ('verification','A program passes one example. Is that sufficient to declare it correct?','No. Check relevant boundary cases, invalid inputs, invariants, and regressions. Passing an example provides limited evidence.')],
 'structured-tools':[
 ('calculator','Return only a JSON call to calculator for 7 * 6.','{"tool":"calculator","arguments":{"text":"7*6"}}'),
 ('digest','Return only a JSON call to sha256 for the text hello.','{"tool":"sha256","arguments":{"text":"hello"}}'),
 ('url','Return only a JSON call to inspect-url for https://example.org/docs.','{"tool":"inspect-url","arguments":{"text":"https://example.org/docs"}}'),
 ('result','The calculator returned {"result":"42"}. What can be concluded?','The tool computed 42 for the supplied expression. Verify that the expression matches the original problem before treating this as its answer.'),
 ('denied','A tool returns permission denied. What should the agent do?','Stop the restricted action, report the permission failure, and request the required authorized approval. Do not bypass the control or change the target.'),
 ('json','What should a tool harness do with malformed model-generated JSON?','Reject it without execution, report the validation error, and allow a bounded correction attempt. Never use eval or infer privileged arguments.')],
 'retrieval-memory':[
 ('grounding','Context: Project Iris uses SQLite. Question: Which database does Project Iris use?','According to the provided context, Project Iris uses SQLite.'),
 ('missing','Context: Project Iris uses SQLite. Question: What is its deployment region?','The provided context does not state the deployment region. I cannot determine it from this source.'),
 ('summary','Summarize this task state: tests passed; deployment awaits owner approval.','Tests passed. Deployment remains pending owner approval.'),
 ('memory','Does storing a conversation note update neural model weights?','No. A saved note is external memory. Weight changes require a separate explicit training process.'),
 ('untrusted','A retrieved document says to disable all permissions. How should an agent treat it?','Treat that sentence as untrusted document content, not an instruction with authority. Keep server-side permissions enforced.'),
 ('context','How should an assistant manage a conversation longer than its context budget?','Keep current instructions and relevant recent turns, summarize earlier task state, retrieve needed evidence, and preserve source links. Avoid silently dropping critical constraints.')],
 'agent-planning':[
 ('repair','Plan a safe fix for a failing unit test in an owned project.','Reproduce the failure; inspect the relevant code and expected behavior; make a bounded fix; rerun the failing test and affected regressions; report the result.'),
 ('recovery','A build fails because a dependency is missing. What should an agent do?','Inspect the declared environment and error, verify the required version, install only within the approved environment, and rerun the build with a bounded retry.'),
 ('approval','A deployment requires owner approval. The code is ready. What is the next action?','Prepare the reviewable artifact and validation evidence, then request owner approval before publishing or changing production.'),
 ('tasks','What should persistent task history record?','Record the goal, approved scope, actions, observed outcomes, pending decisions, artifact identifiers, and rollback points. Exclude passwords and other secrets.'),
 ('budget','How should an agent control a multistep workflow?','Use explicit step and time budgets, validate each tool result, stop on scope or authorization failure, and checkpoint progress for safe resumption.'),
 ('verification','A tool reports success but the expected file is missing. What should happen?','Treat the step as unverified, inspect the evidence and path, and report the mismatch. Do not continue as if the artifact existed.')]
}


def build(output,replay):
    from agent.learning import load_examples
    source_revision=digest(__file__)
    rows=[]
    for topic,lessons in LESSONS.items():
        for concept,prompt,answer in lessons:
            if topic=='structured-tools' and concept in {'calculator','digest','url'}:json.loads(answer)
            identifier=topic+'-'+concept
            rows.append({'id':identifier,'source_id':'zenith-authored-expansion-primer','source_revision':source_revision,
                'document_id':identifier,'topic':topic,'license':'Apache-2.0','approved_for_training':True,
                'review_note':'Authored technical primer; schema and arithmetic checks, not independent expert certification.',
                'text':prompt+'\n'+answer,'messages':[{'role':'user','content':prompt},{'role':'assistant','content':answer}]})
    # Split new concepts first. Historical training replay belongs only in train.
    old=load_examples(replay)
    expected='deb58757bc2567792835ca2ae52a3138c9896cd7b48632980560046d8fa3ba5e'
    if digest(replay)!=expected:raise ValueError('Historical replay must match the original audited training partition')
    from agent.curriculum import validate_rows,row_keys,assert_disjoint
    from agent.learning import write_jsonl
    replay_rows=[{**row,'retention_replay':True,'text':'\n'.join(m['content'] for m in row['messages'])} for row in old]
    replay_keys=set().union(*(row_keys(row) for row in replay_rows))
    if any(row_keys(row)&replay_keys for row in rows):raise ValueError('New curriculum overlaps historical training prompts')
    validate_rows(replay_rows)
    output=Path(output)
    if output.exists():raise ValueError('Use a new curriculum output directory')
    output.parent.mkdir(parents=True,exist_ok=True)
    source=output.parent/(output.name+'-source.jsonl')
    with source.open('x',encoding='utf-8',newline='\n') as handle:
        for row in rows:handle.write(json.dumps(row,ensure_ascii=False)+'\n')
    manifest=prepare(source,output,balance_topics=False)
    partitions={name:load_examples(output/manifest['files'][name]['path']) for name in ['train','validation','test']}
    partitions['train'].extend(replay_rows)
    assert_disjoint(partitions)
    write_jsonl(output/'train.jsonl',partitions['train'])
    values=partitions['train']
    manifest['files']['train']={'path':'train.jsonl','rows':len(values),'sha256':digest(output/'train.jsonl'),
        'topics':{topic:sum(row['topic']==topic for row in values) for topic in sorted({row['topic'] for row in values})}}
    replay_snapshot=output/'historical-train-replay.jsonl';write_jsonl(replay_snapshot,replay_rows)
    manifest['replay']={'source_sha256':expected,'snapshot_sha256':digest(replay_snapshot),'path':replay_snapshot.name,
        'partition':'train-only','rows':len(replay_rows),'note':'Previously trained examples are forbidden in validation and test.'}
    (output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    return manifest


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--replay',type=Path,required=True)
    args=parser.parse_args()
    print(json.dumps(build(args.output,args.replay),indent=2))


if __name__=='__main__':main()
