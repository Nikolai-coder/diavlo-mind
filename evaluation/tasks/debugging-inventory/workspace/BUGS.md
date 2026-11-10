# Reported problems

**#1 — Restocking loses stock.**
We had 5 units of `A-100`, received 3 more and called `restock("A-100", 3)`. The system now says we have 3. (This is the failing test.)

**#2 — Two warehouses see each other's items.**
We create one `Inventory()` per warehouse. After adding items to the first warehouse, the second one — created with no arguments — already contains them.

**#3 — CSV export has shifted columns.**
An item named `Bolt, hex (M8)` exports as five columns instead of four, and our import script then reads the wrong quantity. Names with double quotes break as well.

**#4 — Low-stock report misses items.**
With the threshold set to 10, an item with exactly 10 units is not listed. The README says "at or below".

**#5 — Customer charged one cent too little.**
A 9.95 item with a 15% discount was charged 8.45. The correct price is 8.46 (845.75 cents rounds half up).
