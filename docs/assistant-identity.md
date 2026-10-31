# Assistant identity and model provenance

Zenith is maintained in [n8storm/Zenith](https://github.com/n8storm/Zenith).
The hosted deployment uses the existing pinned Qwen/Qwen2.5-0.5B-Instruct base,
from Alibaba Cloud's Qwen team, and its configured Zenith adapter. The application
and the upstream foundation model have distinct identities. This patch does not
rename upstream files, remove license notices, retrain weights or switch models.

The reported question, `Who created you`, previously produced `I am Zeno, a large
language model developed by Alibaba Cloud.` A live pre-change probe reproduced
that wrong application identity. The compact prompt supplied only Zenith's name;
free-form neural self-description could drift to the base-model attribution.

Clear, bounded identity questions now use reviewed application metadata and the
configured backend description in both response modes. The interface labels this
`Application identity · configured model provenance` and records zero model calls;
this is an application fact, not a new learned capability or confidence score.
Both model prompt styles also receive consistent project identity and configured
provenance for follow-up questions. Unknown model authorship is explicitly
unverified; private checkpoint paths and credentials are not disclosed.

Matching is anchored to direct identity questions. Questions about other people,
translation, code and special output formats continue through the normal model
path. A user history containing a wrong identity remains preserved, but cannot
override the reviewed identity answer. Prompt/provenance changes alter evaluation
configuration fingerprints so old calibration is not silently reused.

Tests cover varied identity questions, both response modes, negative routing,
unknown/switched backends, public guest HTTP/SSE, old history retention and
calibration invalidation. Live acceptance must check the actual public response
after deployment. This fixes the demonstrated identity failure; it does not
guarantee correctness for arbitrary mathematical, factual or programming tasks.

Rollback: deploy the previous source release against the same unchanged model
and durable volume. No database schema or checkpoint migration is involved.
