"""Runtime package (ANES v2, Phase 2).

The Execution Runtime. Per ADR-005 it has two separable concerns:
  - control flow  : pipeline.py  (Task -> stages, gating, ordering)
  - resource flow : registry_loader / resolver / normalizer / compiler

The vertical spine proven in Phase 2:
  RegistryLoader -> Validator(gate) -> Resolver -> Normalizer -> Compiler
  -> TaskPackage + BuildManifest
"""
