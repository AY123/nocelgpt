# V2-004 exact local runner verifier candidate

This record supports only the user-authorized local code pin based on dev_gpt 1449da9783e36aa4704d45be9d35a3f2a39d4b52. No push/MR, security disposition/approval/consumer, runner registration or permission mutation is authorized here. Canonical stays45 OPEN; V2-004 IN_PROGRESS and P0 NOT_VERIFIED.

The technical review consumes the existing immutable clean-checkout scope at a3496f79b6abeeaf3a4c7be950ddc2b2d09bb7c6, ref followup-20261004/scope-ci-v3.json. It is an ancestor commit separate from the implementation candidate, so no same-candidate self-pin or ancestry bypass is used. Original findings remain visible.

The verifier requires a dedicated protected/locked project runner, exact exclusive project membership, no untagged jobs, fixed policy/job/runner tag, and each actual runner must cover its own jobs' entire tag set. Fields missing/null/malformed remain unverified; no warning-only acceptance. Source facts and permissions are distinct; even matching metadata leaves permission UNKNOWN and acceptance false.

Prior58 new controls are preserved;13 additional cases cover tag-set scheduling contradictions, multiple actual runners, malformed API responses and runner identity mismatches. Fresh focused72 PASS is supporting logic evidence, not full gate or real runner acceptance. Full pre-pin and post-pin checks must be freshly generated in separate clean checkouts at the exact same candidate SHA; artifacts go outside plan and are not borrowed from the primary worktree. The primary user audit/prompt/tool configuration modifications are excluded and preserved.

Implementation and verification are the same operator assisted by agents; independent human review is pending. The maximum status after clean exact-revision checks is READY_FOR_INDEPENDENT_REVIEW for the verifier implementation. Real trusted execution and V2-004/P0 acceptance remain unverified.

Tag scheduling basis: https://docs.gitlab.com/ci/runners/configure_runners/#a-runner-and-a-job-have-multiple-tags
