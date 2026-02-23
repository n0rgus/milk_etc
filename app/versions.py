"""Central component version registry.

Versioning policy (order-of-magnitude buckets):
- 1.x.x: Core web UI templates/layouts
- 2.x.x: Backend API/routes/services
- 3.x.x: PriceWatch capture extension
- 4.x.x: Link helper extension

Increment the patch component for each code change in the relevant component.
"""

CORE_UI_VERSION = "1.0.1"
API_VERSION = "2.0.1"
CAPTURE_EXTENSION_VERSION = "3.0.1"
LINK_HELPER_EXTENSION_VERSION = "4.0.1"
