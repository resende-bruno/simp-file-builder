# simp-file-builder

Generate native [Software Ideas Modeler](https://www.softwareideas.net/) project files (`.simp`) from Python.

The `.simp` format is undocumented and XMI import is a paid feature. This package writes the native format directly, so the result opens with File > Open in the free edition.

Supported diagrams: use case, sequence (`loop`/`opt` fragments), class (with packages), activity.
Not supported, schema unconfirmed: ER diagrams, `alt` fragments, interfaces.

## Install

```bash
pip install simp-file-builder
```

## Usage

```python
from simp_file_builder import SimProjectFile, UseCaseDiagram, SequenceDiagram, ClassDiagram, ActivityDiagram

proj = SimProjectFile("Shop", "Me")

uc = UseCaseDiagram("Use cases", "Shop")
uc.add_actor("Customer")
uc.add_usecase("Buy")
uc.add_association("Customer", "Buy")
proj.add(uc)

sq = SequenceDiagram("Checkout", actors=uc.actors)   # reuse the actor as a lifeline
sq.add_lifeline("Customer")
sq.add_lifeline("Shop")
sq.add_message("Customer", "Shop", "call", "checkout()")
proj.add(sq)

cd = ClassDiagram("Domain")
cd.add_package("shop")
cd.add_class("Order", "shop", attributes=[("id", "int")], operations=[("total", "decimal", [])])
cd.add_class("Item", "shop")
cd.add_association("Order", "Item", label="contains")
proj.add(cd)

ad = ActivityDiagram("Flow")
start = ad.add_initial(100, 20)
step = ad.add_action("Validate", 50, 80)
end = ad.add_final(100, 200)
ad.add_flow(start, step)
ad.add_flow(step, end)
proj.add(ad)

proj.write("shop.simp")
```

Types for attributes, parameters and return values: `"int"`, `"string"`, `"boolean"`, `"decimal"`, `"date"`, or `None`.

## Disclaimer

This is an independent, unofficial project. It is not affiliated with, endorsed by, or supported by Software Ideas Modeler or its author.

- The `.simp` structure was worked out by inspecting files saved from a legitimately licensed copy of the application, solely so other tools can produce files it opens (interoperability).
- No source code, binaries, assets, or documentation from Software Ideas Modeler are included or redistributed. Everything here is original Python code that writes plain XML.
- "Software Ideas Modeler" is a trademark of its respective owner and is used only to identify the file format.
- The software is provided as-is, without warranty, under the MIT License. Use it at your own risk; the format may change in future versions of the application.

## Development

```bash
pip install -e .
python tests/test_simp_file_builder.py
```

The schema was worked out by inspecting files saved by SIM v15.21. If you extend it, open the result in SIM before trusting a new element type.
