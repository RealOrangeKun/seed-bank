"""ML platform infrastructure: registry, builders, backends, manager, pipelines.

Importing this package does **not** pull in torch — only the registry +
DTOs are loaded. The heavy imports live in the concrete backend / builder
modules and only fire when the inference worker actually uses them.
"""
