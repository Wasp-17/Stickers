# Stickers

This is our first project developed together with ChatGPT — **Stickers**.

The project is an online store where users can choose stickers they like either from the catalog or create stickers based on their own images.

The core idea is simple: **take only what you need, and don't take what is usually added as an unnecessary extra.**

The goal of the project is to help users express and emphasize their individuality through a wide variety of images presented as physical stickers.
## Project status

The project is currently in the early development stage.

Sticker artwork and other image assets are intentionally kept outside this public
repository. The local site preview needs separately supplied WEB preview files in
`images/`; production MASTER and ART files must remain in private storage. Public
catalog metadata lists image filenames but does not contain the image bytes.

Current site, hardware-test and Printnik status as of 23 October 2026 is recorded
in [PROJECT_STATUS_2026-10-23.md](PROJECT_STATUS_2026-10-23.md). The detailed
Printnik instructions and calibration results are in `printnik/README.md` and
`printnik/docs/CALIBRATION_LOG.md`. Some older prototype figures below are retained
as development history and do not describe the current production profile.

## Local preview

Run `start-site.cmd`, then open the local HTTP links it provides. Opening
`catalog.html` directly from disk does not allow the browser to load catalog data.
The catalog currently shows the original sticker and 26 images from `images/`.
The sticky search field filters these cards by their provisional names as you type;
it does not change the current order or the sheet layout. Exact name matches appear first.
Select A–F and a positive integer quantity. A single click selects an image and
opens a larger view; a double click adds that image. Enter in the quantity field
adds the currently selected image.
Both use the same validation and partial-addition flow. Holding Enter does not
repeat additions. Double-click a sticker on the sheet to
remove one copy. Only necessary sheets are shown, with a maximum of ten.
The current order and delivery-address data are stored in the browser and restored
after reload. The same order is shown on `account.html` for the signed-in local user.

The start page includes a local single-user registration prototype. The account,
password hash and signed-in state are stored only in the current browser. It is
intended for interface testing and must be replaced with server-side authentication
before deployment.

The cabinet shows the current layout order and multiple named orders saved in the
cart. A cart order can be opened, renamed or deleted after confirmation. The former
Drafts section and all locally stored draft data were removed as redundant. Checkout uses
a structured postal-address form. Signed-in local users can save multiple addresses,
select them during checkout and remove them in the cabinet. Order history and
favorites remain prepared sections without stored data.

The cart stores at most 30 orders. Saving a thirty-first new order is refused without
deleting an older order or clearing the active layout; the interface directs the
customer to the full cart in the cabinet. Existing cart orders can still be edited
and saved while the cart is full.

## Layout prototype

`layout.js` contains the isolated packing engine and its configuration. It uses
largest-first rectangular packing with optional 90-degree rotation, no mirroring,
and reserved margins, cutting gaps and a technical marking strip.

Geometry is measured in millimetres. The approved size boxes are A 30x30,
B 50x50, C 75x75, D 100x100 and E 125x125 mm. An image is proportionally fitted into
its selected box, and the finished cut contour must not exceed that box. Size F
fits the image into the calibrated A4 work area. The current work area still uses
provisional 12 mm margins, a 4 mm gap and a 12 mm technical strip; these values
are not yet an approved Epson EcoTank L8050 / Silhouette Cameo 5 Alpha production
profile. Real print margins, registration marks and cut contours require hardware
calibration. See `PRINT_PRODUCTION_PROFILE.md` for the recorded decisions.
The planned local production application, order-message format, redundant delivery
channels and local master-file catalog are recorded in `PRINTNIK_ARCHITECTURE.md`.

Packing is currently rectangle-based. It deliberately reserves the bounding
rectangle around each future cut contour, so it does not yet place small stickers
inside the free corners around circles, splashes or separate droplets.
The algorithm is a packing heuristic, not a guarantee of the global minimum.

Catalog results are rendered incrementally. The first 60 matching sticker cards
are created on opening a selection; each press of the continuation button appends
up to 60 more while keeping the earlier cards on screen. Image elements for later
results are not created until their batch is requested.

Catalog search uses a compact primary row. A non-empty text query automatically
searches the whole catalog when no section is selected. With a selected section,
the query searches inside that section unless the user explicitly switches to the
whole catalog. Empty-query browsing still requires a section; character, role and
mood remain unavailable until one is selected. Text matches are ranked by exact
full title, whole title words, Russian word forms, one tolerated typo across the
query, and only then a partial-word match. Words shorter than four characters do
not receive typo correction. Additional filters open in a separate panel and
active filters appear as removable chips. The dormant sort control remains
available in code for later return when real popularity and recency data are present.

Ordinary section browsing uses a stable mixed order. A random `mix` key is written
to the catalog URL on a new visit; reload, browser Back/Forward and a shared URL
reproduce the same complete order, while a new visit receives a new key. Result
batches are slices of one permutation, so loading more cannot repeat or discard
earlier cards. The ranking layer also prevents runs longer than two cards from the
same available semantic category. Ten leading positions are reserved for future
aggregate ranking: paid-order count and units have the highest priority, favorites
come next, and catalog addition date is the final priority. Local favorite and paid
order events can already be recorded in `StickerStore`; shared ordering consumes
only synchronized `catalog.ranking_stats`, so recipients of one link cannot see a
different order because of private browser data.

An order is also capped at 350 stickers: with the current provisional margins,
technical strip and cutting gap, one sheet holds 5 by 7 square size-A stickers,
or 35 per sheet and 350 across ten sheets. This absolute count limit applies even
when a narrow image could physically pack more densely, and must be recalibrated
with the production profile. An addition exceeding either limit fills the available capacity first, preserving
the existing order. A dialog reports requested, added and remaining quantities and
allows the customer to save the current order to the cart and continue with a new
layout without paying. Checkout remains a separate optional action. The checkout review shows the
selected items, every sheet and a postal-address field. The address stays only in
the current page; no order is submitted and no payment is taken. Continuing as a
new order awaits actual checkout support. Saved-address handling is not implemented
yet.

Run geometry and quantity checks with `node layout.test.js`.
