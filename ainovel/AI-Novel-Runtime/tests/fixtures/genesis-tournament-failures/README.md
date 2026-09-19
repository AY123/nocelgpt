# Genesis tournament failure fixtures

These are the minimal retained records from the discarded 2026-08-04 live
diagnostic runs.  They preserve the two distinct failure modes without checking
in duplicate outline, ledger, and analysis artifacts.

- `parse-failure.json`: a provider returned text that did not satisfy the old
  pairwise contract and was incorrectly collapsed into an ordinary tie.
- `connection-failure.json`: both Claude orderings failed to connect.
- `live-acceptance-20260805.json`: compact audit summary for the real dual-model
  acceptance sequence. It retains the failed Claude prompt-only attempts and the
  final forced-tool-schema pass; both providers ultimately passed on one frozen
  candidate hash and agreed on the same advisory winner.

Neither fixture is successful tournament evidence.
