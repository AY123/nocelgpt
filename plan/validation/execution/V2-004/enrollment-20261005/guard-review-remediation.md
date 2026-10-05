# New protected guard review

Same-operator supporting review found three P1 issues in the new draft: candidate overlay code executed by tests despite self exclusion; root Python module shadowing outside the inventory; preinstalled virtual environment and uv configuration outside coverage. These must be remediated before configuration activation or execution. This record does not accept the guard or close any security finding. Accepted 9fe verifier/root CI remain unchanged.
