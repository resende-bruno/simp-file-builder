"""Self-check: build every diagram type, parse the result, verify no dangling id/iid refs."""
import xml.etree.ElementTree as ET

from simp_file_builder import ActivityDiagram, ClassDiagram, SequenceDiagram, SimProjectFile, UseCaseDiagram

ID_REFS = ["owner", "from", "to", "property-ref", "lifeline-ref", "container"]
IID_REFS = ["from-iid", "to-iid", "container-iid"]


def build():
    proj = SimProjectFile("Demo & <Co>", 'O"Author')

    uc = UseCaseDiagram("Use cases", "Shop <system>")
    uc.add_actor("Customer")
    uc.add_actor("Admin")
    for name in ["Browse", "Buy & pay", "Refund"]:
        uc.add_usecase(name)
    uc.add_association("Customer", "Browse")
    uc.add_association("Admin", "Refund")
    uc.add_include("Buy & pay", "Browse")
    uc.add_extend("Refund", "Buy & pay")
    proj.add(uc)

    sq = SequenceDiagram("Checkout", actors=uc.actors)
    for ll in ["Customer", "Shop", "Bank"]:
        sq.add_lifeline(ll)
    sq.add_message("Customer", "Shop", "call", "checkout()")
    sq.start_fragment("loop", "for each item")
    sq.add_message("Shop", "Shop", "call", "reserve(item)")
    sq.end_fragment()
    sq.start_fragment("opt", "card")
    sq.add_message("Shop", "Bank", "call", "charge(amount)")
    sq.add_message("Bank", "Shop", "reply", "ok")
    sq.end_fragment()
    proj.add(sq)

    cd = ClassDiagram("Domain")
    cd.add_package("shop")
    cd.add_package("billing")
    cd.add_class("Order", "shop", [("id", "int"), ("total", "decimal")],
                 [("add", None, [("item", "string")]), ("total", "decimal", [])])
    cd.add_class("Item", "shop", [("name", "string")])
    cd.add_class("Invoice", "billing", [("date", "date")])
    cd.add_class("Loose")
    cd.add_association("Order", "Item", label="contains")
    cd.add_generalization("Invoice", "Order")
    cd.add_dependency("billing", "shop", "uses")
    proj.add(cd)

    ad = ActivityDiagram("Flow")
    start = ad.add_initial(100, 20)
    a = ad.add_action("Validate", 50, 80)
    d = ad.add_decision("ok?", 130, 160)
    b = ad.add_action("Ship", 50, 300)
    end = ad.add_final(100, 400)
    ad.add_flow(start, a)
    ad.add_flow(a, d)
    ad.add_flow(d, b, "yes")
    ad.add_flow(d, end, "no")
    ad.add_flow(b, end)
    proj.add(ad)
    return proj


def check(xml):
    root = ET.fromstring(xml)  # raises on malformed XML (e.g. unescaped & or ")
    ids = {e.get("id") for e in root.iter()} - {None}
    iids = {e.get("iid") for e in root.iter()} - {None}
    for e in root.iter():
        for attr in ID_REFS:
            assert e.get(attr) in (None, "") or e.get(attr) in ids, f"dangling {attr}={e.get(attr)}"
        for attr in IID_REFS:
            assert e.get(attr) is None or e.get(attr) in iids, f"dangling {attr}={e.get(attr)}"
    assert [d.get("type") for d in root.iter("diagram")] == ["uml-usecase", "uml-sequence", "uml-class", "uml-activity"]
    assert [d.get("order-index") for d in root.iter("diagram")] == ["1", "2", "3", "4"]
    assert root.find("meta/name").text == "Demo & <Co>"
    # shared actor: declared once, placed on both diagrams
    customer = [e for e in root.iter("item") if e.get("type") == "actor" and e.get("name") == "Customer"]
    assert len(customer) == 1
    assert sum(1 for e in root.iter("item") if e.get("id") == customer[0].get("id") and e.get("iid")) == 2
    # boundary placed first in the use-case layer so use cases draw on top of it
    layer = next(root.iter("layer"))
    assert layer[0].get("id") == next(e for e in root.iter("item") if e.get("type") == "system-boundary").get("id")


if __name__ == "__main__":
    proj = build()
    xml = proj.render()
    check(xml)
    proj.write("demo.simp")
    print(f"ok: {len(xml)} bytes, demo.simp written")
