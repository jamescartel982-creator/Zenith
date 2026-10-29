"""Frozen, locally authored recipe grammar v1, Apache-2.0.

These are 100,000 labeled combinations, not independently evaluated abilities.
Keep v1 stable: a changed renderer requires a new version and explicit migration.
No external model, copyrighted corpus, executable plugin or training is used.
"""
from functools import lru_cache
import hashlib
from pathlib import Path

VERSION = 1
PREFIX = 'x-recipes-'
NOTICE = 'Generated workflow recipe; not independently evaluated and not neural training.'

# Title, bounded subject scope, supporting reference. The last ten are protected.
SUBJECTS = (
    ('Algebra', 'equations, identities and explicit domains', 'khan'),
    ('Calculus', 'limits, derivatives, integrals and assumptions', 'mit-ocw'),
    ('Linear algebra', 'vectors, matrices, dimensions and rank', 'mit-ocw'),
    ('Probability', 'events, conditioning and sample spaces', 'khan'),
    ('Statistics', 'estimands, sampling and uncertainty', 'scipy'),
    ('Discrete mathematics', 'sets, graphs and finite structures', 'mit-ocw'),
    ('Number theory', 'integer properties and proof conditions', 'khan'),
    ('Geometry', 'figures, coordinates and stated axioms', 'khan'),
    ('Numerical methods', 'approximation, stability and error bounds', 'scipy'),
    ('Optimization', 'objectives, feasible sets and constraints', 'scipy'),
    ('Mechanics', 'forces, motion, units and boundary conditions', 'openstax'),
    ('Thermodynamics', 'energy, systems and process assumptions', 'openstax'),
    ('Electromagnetism', 'fields, circuits and physical units', 'openstax'),
    ('Optics', 'light, geometry and approximation limits', 'openstax'),
    ('Quantum foundations', 'states, observables and interpretation limits', 'mit-ocw'),
    ('General chemistry', 'reactions, quantities and conservation', 'openstax'),
    ('Materials science', 'material properties and measurement conditions', 'mit-ocw'),
    ('Biology', 'biological mechanisms and supporting observations', 'openstax'),
    ('Ecology', 'populations, ecosystems and confounding variables', 'openstax'),
    ('Earth science', 'geological evidence and timescales', 'openstax'),
    ('Astronomy', 'observations, physical models and distance scales', 'openstax'),
    ('Scientific method', 'hypotheses, controls and falsifiability', 'openstax'),
    ('Experimental design', 'controls, randomization and measurement', 'scipy'),
    ('Measurement', 'units, calibration and uncertainty propagation', 'scipy'),
    ('Research synthesis', 'retrieved evidence, disagreements and gaps', 'loc'),
    ('Python', 'Python programs, runtime behavior and tests', 'pytorch'),
    ('JavaScript', 'JavaScript code, asynchronous behavior and tests', 'nist-ssdf'),
    ('TypeScript', 'types, interfaces and runtime validation', 'nist-ssdf'),
    ('Rust', 'ownership, types and tested program behavior', 'nist-ssdf'),
    ('Go', 'interfaces, concurrency and tested program behavior', 'nist-ssdf'),
    ('C programming', 'memory lifetimes, bounds and defined behavior', 'nist-ssdf'),
    ('C++ programming', 'resource ownership, types and defined behavior', 'nist-ssdf'),
    ('Java', 'types, object lifecycles and tested behavior', 'nist-ssdf'),
    ('SQL', 'query grain, joins, nulls and execution plans', 'pandas'),
    ('Bash', 'quoting, exit status and controlled scripts', 'nist-ssdf'),
    ('Software architecture', 'module boundaries and explicit tradeoffs', 'nist-ssdf'),
    ('API design', 'contracts, compatibility and error behavior', 'nist-ssdf'),
    ('Database design', 'keys, integrity and transaction boundaries', 'pandas'),
    ('Testing', 'observable behavior and meaningful test coverage', 'nist-ssdf'),
    ('Debugging', 'reproduction, causal hypotheses and verification', 'nist-ssdf'),
    ('Code review', 'correctness, maintenance and regression risks', 'nist-ssdf'),
    ('Version control', 'reviewable changes and reversible history', 'nist-ssdf'),
    ('Algorithms', 'correctness, complexity and input constraints', 'mit-ocw'),
    ('Data structures', 'invariants, operations and resource costs', 'mit-ocw'),
    ('Concurrency', 'ordering, synchronization and failure cases', 'nist-ssdf'),
    ('Distributed systems', 'consistency, partial failure and recovery', 'nist-ssdf'),
    ('Linux operations', 'authorized configuration and system behavior', 'nist-ssdf'),
    ('Windows operations', 'authorized configuration and system behavior', 'nist-ssdf'),
    ('Containers', 'isolation boundaries, images and resource limits', 'nist-ssdf'),
    ('Cloud architecture', 'service boundaries, costs and reliability', 'nist-ssdf'),
    ('Networking', 'protocols, addressing and observed connectivity', 'mit-ocw'),
    ('System observability', 'logs, metrics and trace evidence', 'nist-ssdf'),
    ('Reliability', 'failure modes, recovery and service objectives', 'nist-ssdf'),
    ('Capacity planning', 'measured demand, quotas and headroom', 'scipy'),
    ('Backups and recovery', 'restore evidence, retention and integrity', 'nist-ssdf'),
    ('Machine learning', 'data splits, objectives and generalization', 'pytorch'),
    ('Deep learning', 'training dynamics and held-out evaluation', 'pytorch'),
    ('Transformers', 'attention, context and architecture constraints', 'pytorch'),
    ('Language processing', 'language tasks and evaluation assumptions', 'pytorch'),
    ('Computer vision', 'image tasks and measurement limitations', 'pytorch'),
    ('AI agents', 'bounded plans, tools and execution evidence', 'nist-ai'),
    ('Model evaluation', 'frozen tasks, baselines and regressions', 'nist-ai'),
    ('Model calibration', 'confidence, abstention and held-out evidence', 'nist-ai'),
    ('Retrieval systems', 'relevance, attribution and account isolation', 'nist-ai'),
    ('Prompt design', 'explicit instructions and measured task outcomes', 'nist-ai'),
    ('Data cleaning', 'missingness, duplicates and reversible transforms', 'pandas'),
    ('Data visualization', 'encodings, axes and supported comparisons', 'pandas'),
    ('Time series', 'temporal order, leakage and evaluation windows', 'pandas'),
    ('Tabular analysis', 'row grain, denominators and exact arithmetic', 'pandas'),
    ('Data pipelines', 'schemas, provenance and failure recovery', 'pandas'),
    ('Data quality', 'freshness, completeness and consistency', 'pandas'),
    ('Data provenance', 'source revisions, rights and transformations', 'nist-ai'),
    ('Document analysis', 'supplied text, citations and extraction limits', 'loc'),
    ('Technical writing', 'audience, evidence and precise claims', 'loc'),
    ('Editing', 'meaning preservation, clarity and factual checks', 'gutenberg'),
    ('Explanation design', 'reader needs, examples and explicit limits', 'khan'),
    ('Lesson planning', 'objectives, practice and assessment', 'khan'),
    ('Study planning', 'goals, feedback and realistic schedules', 'khan'),
    ('Project planning', 'scope, dependencies and completion criteria', 'nist-ssdf'),
    ('Decision analysis', 'alternatives, assumptions and tradeoffs', 'scipy'),
    ('Economic reasoning', 'incentives, mechanisms and confounders', 'openstax'),
    ('Financial literacy', 'risk, costs and educational examples', 'investor'),
    ('Budget analysis', 'cash flows, categories and reconciliations', 'investor'),
    ('Investment research', 'sourced evidence, uncertainty and risk; no orders', 'investor'),
    ('Historical analysis', 'primary sources, chronology and uncertainty', 'loc'),
    ('Source criticism', 'provenance, bias and independent corroboration', 'loc'),
    ('Knowledge organization', 'entities, relationships and attribution', 'loc'),
    ('Accessibility', 'user needs, barriers and testable alternatives', 'khan'),
    ('Privacy engineering', 'data minimization and consent boundaries', 'nist-ai'),
    ('Human factors', 'user context, errors and inclusive explanations', 'nist-ai'),
    ('Threat modeling', 'authorized assets, trust boundaries and mitigation', 'nist-csf'),
    ('Secure code analysis', 'supplied code, weaknesses and remediation', 'nist-ssdf'),
    ('Incident analysis', 'provided logs, timelines and containment advice', 'nist-ir'),
    ('Forensic reasoning', 'provided evidence, chain of custody and uncertainty', 'nist-ir'),
    ('Malware triage', 'static supplied artifacts; no execution or deployment', 'mitre-d3fend'),
    ('Vulnerability triage', 'authorized findings, impact and remediation', 'nvd'),
    ('Defensive monitoring', 'authorized telemetry, detection and false positives', 'nist-csf'),
    ('Cryptography review', 'documented constructions, assumptions and misuse', 'mit-ocw'),
    ('Lab assessment plans', 'explicitly authorized isolated labs and stop conditions', 'nist-testing'),
    ('Disclosure planning', 'coordinated reporting and mitigation; no intrusion', 'owasp-cheatsheets'),
)

# Title, goal, first step, second step, acceptance check, deliverable.
WORKFLOWS = (
    ('Explain concepts', 'Explain the requested concept without inventing prerequisites.', 'Identify the concept and prerequisites from the request.', 'Give a concrete example and define necessary terms.', 'The explanation separates definitions from assumptions.', 'An explanation with an example and limits'),
    ('Compare approaches', 'Compare user-supplied alternatives against explicit criteria.', 'List alternatives and evaluation criteria.', 'Compare evidence for each criterion without inventing results.', 'The comparison identifies unsupported cells.', 'A comparison table with tradeoffs'),
    ('Plan a task', 'Produce a bounded plan with dependencies and completion criteria.', 'Define the goal, inputs, constraints and stop conditions.', 'Order steps by dependencies and name a verification for each.', 'The plan has a verifiable completion condition.', 'A dependency-aware task plan'),
    ('Review assumptions', 'Find assumptions that materially affect the conclusion.', 'List explicit and implicit assumptions in supplied material.', 'Test which conclusions change when each assumption fails.', 'Unverified assumptions remain visibly unresolved.', 'An assumption register and sensitivity notes'),
    ('Check evidence', 'Check that claims are supported by available evidence.', 'Map each important claim to a supplied or actually retrieved source.', 'Identify missing, conflicting or outdated support.', 'Every cited source was supplied or retrieved during execution.', 'A claim-to-evidence map'),
    ('Design examples', 'Develop a small example illustrating the requested principle.', 'Choose a bounded example and state its assumptions.', 'Work through it and check the result independently where possible.', 'The example does not imply untested generality.', 'A worked example and verification'),
    ('Find edge cases', 'Identify boundary conditions and their expected behavior.', 'State normal inputs, allowed ranges and invariants.', 'Enumerate boundary, empty, invalid and contradictory cases.', 'Expected behavior is explicit for each case.', 'An edge-case checklist'),
    ('Verify a solution', 'Verify a proposed solution using independent checks.', 'Restate the problem constraints and proposed result.', 'Check the result against constraints and a second method if available.', 'Unsupported verification is labeled as incomplete.', 'A verification report'),
    ('Diagnose a failure', 'Investigate a supplied failure without premature certainty.', 'Record observed symptoms and reproducible conditions.', 'Rank hypotheses and propose discriminating, authorized checks.', 'Hypotheses are separate from observed causes.', 'A diagnostic hypothesis table'),
    ('Design an evaluation', 'Define a reproducible evaluation before claiming improvement.', 'Specify task, baseline, metrics and held-out cases.', 'Define thresholds, failure slices and configuration records.', 'Evaluation data does not leak into optimization.', 'An evaluation specification'),
    ('Audit a workflow', 'Inspect a supplied workflow for omissions and failure modes.', 'Map inputs, steps, outputs and responsibility boundaries.', 'Check transitions, exceptional paths and review gates.', 'Each material gap has evidence and a remedy.', 'A workflow audit'),
    ('Build a checklist', 'Translate the task into observable acceptance checks.', 'Extract requirements and identify ambiguous terms.', 'Write checks with inputs, expected outcomes and failure handling.', 'Checks test outcomes rather than repeat instructions.', 'A practical acceptance checklist'),
    ('Summarize material', 'Summarize supplied material while preserving important qualifications.', 'Identify the central question, claims and evidence.', 'Condense the material and retain exceptions and unresolved points.', 'The summary adds no unsupported factual claims.', 'A grounded summary'),
    ('Extract structure', 'Extract structured information from supplied material.', 'Define fields, units and missing-value handling.', 'Extract values with source locations and flag ambiguity.', 'Missing fields are not fabricated.', 'A source-attributed structured record'),
    ('Map dependencies', 'Identify dependencies needed to complete the requested task.', 'List prerequisites, inputs and responsible components.', 'Map ordering, cycles and independent work.', 'A dependency is distinguished from a preference.', 'A dependency map and execution order'),
    ('Assess uncertainty', 'Explain what is known, uncertain and not supported.', 'Separate observations, estimates and assumptions.', 'Identify uncertainty sources and evidence that could reduce them.', 'No numerical confidence is invented without calibration.', 'An uncertainty register'),
    ('Analyze tradeoffs', 'Analyze competing objectives under stated constraints.', 'Identify objectives, limits and stakeholder needs.', 'Compare feasible choices and explain what each sacrifices.', 'Recommendations state conditions under which they change.', 'A tradeoff analysis'),
    ('Review a draft', 'Review a supplied draft for correctness and clarity.', 'Check the draft against its stated goal and audience.', 'Identify supported corrections and explain their effect.', 'Proposed edits preserve meaning unless explicitly changed.', 'A prioritized draft review'),
    ('Create practice', 'Create bounded practice based on the requested material.', 'Define the learning objective and prerequisite knowledge.', 'Create an exercise and a checkable answer or evaluation rubric.', 'Practice examples are labeled as authored examples.', 'A practice exercise and checking rubric'),
    ('Reconcile accounts', 'Reconcile competing accounts or reported results.', 'Align definitions, periods, units and source scope.', 'Compare overlaps and isolate remaining discrepancies.', 'Unresolved differences remain visible.', 'A reconciliation with residual discrepancies'),
    ('Analyze constraints', 'Determine how explicit constraints shape feasible work.', 'List hard limits, preferences and unavailable resources.', 'Identify feasible alternatives and unmet requirements.', 'A missing resource is not represented as available.', 'A feasibility and constraint report'),
    ('Trace provenance', 'Trace conclusions and transformations back to their inputs.', 'Record source identity, revision and permission basis when supplied.', 'Map transformations and distinguish observed from inferred values.', 'Unknown provenance is explicitly marked unknown.', 'A provenance ledger'),
    ('Prepare a handoff', 'Prepare a precise handoff for another authorized person.', 'Record the goal, current evidence and completed work.', 'List unresolved questions, next checks and stop conditions.', 'The handoff excludes credentials and unnecessary personal data.', 'A structured handoff note'),
    ('Plan validation', 'Plan safe checks for a proposed change or conclusion.', 'State the claim, baseline and acceptable validation environment.', 'Specify independent checks, regression cases and rollback conditions.', 'High-impact execution still requires separate authorization.', 'A validation and rollback plan'),
    ('Review conclusions', 'Review whether conclusions follow from the supplied analysis.', 'Map the reasoning from inputs to conclusions.', 'Identify unsupported steps, alternatives and needed corrections.', 'The report can abstain when evidence is insufficient.', 'A conclusion review with open questions'),
)

# Title, review instruction, acceptance check.
LENSES = (
    ('Correctness', 'Check definitions, calculations and logical consistency.', 'Check at least one critical result independently if possible.'),
    ('Evidence', 'Trace factual claims to supplied or actually retrieved evidence.', 'Distinguish source-backed claims from hypotheses.'),
    ('Reproducibility', 'Record inputs, methods, versions and repeatable checks.', 'Another reader can identify the steps needed to reproduce the result.'),
    ('Failure modes', 'Examine plausible failures and explicit stop conditions.', 'State how a failed check would change the recommendation.'),
    ('Resource limits', 'Respect stated time, memory, cost and access limits.', 'Do not describe unavailable resources as operational.'),
    ('Privacy', 'Minimize personal data and exclude credentials from outputs.', 'Use only information needed for the authorized task.'),
    ('Clarity', 'Use consistent terms and expose ambiguous definitions.', 'A reader can distinguish facts, estimates and recommendations.'),
    ('Boundary cases', 'Check empty, extreme and contradictory cases where applicable.', 'State where the method or conclusion no longer applies.'),
    ('Retention', 'Preserve existing behavior, records and reversible decisions.', 'Identify regressions or information lost by a proposed change.'),
    ('Authorization', 'Keep actions inside explicit permissions and supplied scope.', 'Instructions do not grant tools, network access or administrator rights.'),
)

# Title, audience adaptation. Adaptation is instruction content, not label padding.
AUDIENCES = (
    ('Beginner', 'Define unfamiliar terms and use a small worked example.'),
    ('Practitioner', 'Give actionable steps with assumptions and acceptance checks.'),
    ('Reviewer', 'Prioritize evidence, counterexamples and unresolved risks.'),
    ('Decision maker', 'Lead with the decision, tradeoffs and confidence limitations.'),
)

PUBLIC_SUBJECTS = 90
TOTAL = len(SUBJECTS) * len(WORKFLOWS) * len(LENSES) * len(AUDIENCES)


@lru_cache(maxsize=1)
def fingerprint():
    return hashlib.sha256(Path(__file__).read_bytes().replace(b'\r\n', b'\n')).hexdigest()


def coordinates(index):
    if type(index) is not int or not 0 <= index < TOTAL:
        raise ValueError('Unknown generated recipe')
    remaining, audience = divmod(index, len(AUDIENCES))
    remaining, lens = divmod(remaining, len(LENSES))
    subject, workflow = divmod(remaining, len(WORKFLOWS))
    return subject, workflow, lens, audience


def render(index):
    subject, task, lens, audience = coordinates(index)
    title, scope, resource = SUBJECTS[subject]
    task_title, goal, first, second, check, deliverable = WORKFLOWS[task]
    lens_title, review, lens_check = LENSES[lens]
    audience_title, adaptation = AUDIENCES[audience]
    return {'id': PREFIX + f'{index:05d}',
        'name': f'Generated: {title} / {task_title} / {lens_title} / {audience_title}',
        'category': 'security' if subject >= PUBLIC_SUBJECTS else 'general',
        'access': 'admin' if subject >= PUBLIC_SUBJECTS else 'public',
        'kind': 'instruction-profile', 'version': VERSION,
        'instruction': f'{NOTICE} Subject: {title}: {scope}. {goal} {review} {adaptation}',
        'workflow': [f'Establish the supplied {title} task, authorized scope and available evidence.', first, second, review, adaptation],
        'checklist': [check, lens_check, 'State unverified assumptions and abstain when necessary; no execution rights are granted.'],
        'deliverable': f'{deliverable}, for {audience_title.lower()}, with the {lens_title.lower()} review lens.',
        'practice': f'Apply this generated recipe to a user-supplied {title} example and review the result; no outcome is pre-validated.',
        'resource_ids': [resource]}
