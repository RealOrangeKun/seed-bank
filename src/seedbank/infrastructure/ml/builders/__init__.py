"""Architecture builders.

Drop a new file here that calls ``@register_builder("<key>-vN")`` to make a
new architecture available. Autodiscovery (see ``registry.py``) scans this
package on first lookup; you do not need to import the new module anywhere.

Files whose name starts with ``_`` are private helpers and skipped by
autodiscovery.
"""
