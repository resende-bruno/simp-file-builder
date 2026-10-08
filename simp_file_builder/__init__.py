"""
Generate Software Ideas Modeler (.simp, SIM v15.21) project files.

Schema derived from inspecting files SIM itself saved; opens via File > Open in the free edition.
Supported: use-case, sequence (loop/opt only), class (+packages), activity.
Unconfirmed, do not guess: ER diagrams, `alt` fragments, interfaces.

    proj = SimProjectFile("Shop", "Me")
    uc = UseCaseDiagram("Use cases", "Shop")
    uc.add_actor("Customer"); uc.add_usecase("Buy"); uc.add_association("Customer", "Buy")
    proj.add(uc)
    proj.write("shop.simp")
"""
import uuid
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import NamedTuple
from xml.sax.saxutils import escape


def hexid():
    return uuid.uuid4().hex


def now():
    return datetime.now().strftime("%m/%d/%Y %H:%M:%S")


def esc(text):
    """XML-escape text for an attribute value."""
    return escape(str(text), {'"': "&quot;"})


_counts = defaultdict(int)


def cid(prefix):
    """Display ids: AC001, AC002, ... Process-global."""
    _counts[prefix] += 1
    return f"{prefix}{_counts[prefix]:03d}"


class Node(NamedTuple):
    """Model id, placement iid, canvas box."""
    id: str
    iid: str
    x: int
    y: int
    w: int
    h: int

    @property
    def center(self):
        return self.x + self.w // 2, self.y + self.h // 2


def meta(change_date=None):
    return (
        f'<meta><authors><author> </author></authors><description />'
        f'<creation-date>{now()}</creation-date><change-date>{change_date or now()}</change-date>'
        f'<revision-count>0</revision-count><version /></meta>'
    )


STYLE = (
    '<style><background-color index="1" color="#FFFFFFFF" /><background-color index="2" color="#FFFFFFFF" />'
    '<background-type type="solid" /></style>'
)
PADDED = 'container-layout="simple"><container-layout padding="10,10,10,10" /></layout>'

# type key -> (type, type-id)
TYPE_MAP = {
    "int": ("Integer", "Uml.Integer"),
    "string": ("String", "Uml.String"),
    "boolean": ("Boolean", "Uml.Boolean"),
    "decimal": ("BigReal", "Uml.BigReal"),
    "date": ("String", "Uml.String"),  # UML has no native Date primitive
}


def _type(key):
    return TYPE_MAP.get(key, ("", ""))


class Diagram:
    """One <diagram>. Subclasses set TYPE."""

    TYPE = ""

    def __init__(self, name):
        self.name = esc(name)
        self.id = hexid()
        self.top_items = []       # project <items>: model elements
        self.abstract_items = []  # diagram <abstract-items>: relations, messages, fragments
        self.layer_items = []     # canvas placements

    def _place(self, node, *, container=None, kind="entity", attrs="", layout="", body="", padded=False):
        """Place `node` on the canvas, optionally inside `container`."""
        cont = f' container="{container.id}" container-iid="{container.iid}"' if container else ""
        tail = PADDED if padded else "/>"
        self.layer_items.append(
            f'<item id="{node.id}" iid="{node.iid}"{cont}{attrs} creation-date="{now()}" order-index="0" type="{kind}">'
            f'<layout {layout}ax="{node.x}" ay="{node.y}" awidth="{node.w}" aheight="{node.h}" '
            f'x="{node.x}" y="{node.y}" width="{node.w}" height="{node.h}" {tail}{body}</item>'
        )

    def _connect(self, rid, a, b, p1=None, p2=None, layout=""):
        """Draw relation `rid` from a to b; endpoints default to centers."""
        x1, y1 = p1 or a.center
        x2, y2 = p2 or b.center
        self.layer_items.append(
            f'<item id="{rid}" iid="{hexid()}" creation-date="{now()}" order-index="0" type="relation">'
            f'<layout {layout}line-style="oblique" lock-start-point="true" lock-end-point="true" lock-to-fields="false" '
            f'auto-path="" x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" start-border-pos="0.5" end-border-pos="0.5" '
            f'start-local-pos="30" end-local-pos="30" name-position="0,20">'
            f'<points><point x="{x1}" y="{y1}" /><point x="{x2}" y="{y2}" /></points></layout>'
            f'<relation from="{a.id}" from-iid="{a.iid}" to="{b.id}" to-iid="{b.iid}" /></item>'
        )

    def _association(self, a, b, assoc_type="association", label=None):
        """Relationship with start/end roles backed by two property items."""
        rid = hexid()
        p1, p2 = hexid(), hexid()
        for p in (p1, p2):
            self.top_items.append(
                f'<item id="{p}" cid="{cid("PROP")}" type="property" owner="{rid}" creator="" '
                f'creation-date="{now()}" visibility="private" />'
            )
        name = f' name="{esc(label)}"' if label else ""
        self.abstract_items.append(
            f'<item id="{rid}" cid="{cid("REL")}" type="relationship"{name} creator="" creation-date="{now()}" '
            f'from="{a.id}" to="{b.id}" visibility="package"><owned-items />'
            f'<relation from="{a.id}" to="{b.id}" derived="false">'
            f'<start-role id="umlar-{uuid.uuid4()}" name="" navigability="" association-type="{assoc_type}" '
            f'visibility="private" property-ref="{p1}" />'
            f'<end-role id="umlar-{uuid.uuid4()}" name="" navigability="" association-type="{assoc_type}" '
            f'visibility="private" property-ref="{p2}" /></relation></item>'
        )
        self._connect(rid, a, b, layout=(
            'start-role-position="25,15" end-role-position="25,-15" '
            'start-multiplicity-position="25,-15" end-multiplicity-position="25,15" '
        ))
        return rid

    def render(self, order_index=1):
        return (
            f'<diagram type="{self.TYPE}" id="{self.id}" name="{self.name}" order-index="{order_index}" '
            f'expanded="true" uid="" name-style="" auto-routed-paths="false" default-line-style="default" '
            f'view-location="0,0" zoom="0.8">{STYLE}{meta()}'
            f'<abstract-items>{"".join(self.abstract_items)}</abstract-items>'
            f'<layer id="{hexid()}" name="Default" visible="true" enabled="true" locked="false">'
            f'{"".join(self.layer_items)}</layer></diagram>'
        )


class UseCaseDiagram(Diagram):
    """Actors, system boundary with use cases, associations, include/extend."""

    TYPE = "uml-usecase"

    def __init__(self, name, boundary_name):
        super().__init__(name)
        self.actors = {}    # name -> Node
        self.usecases = {}  # name -> Node
        self.boundary = Node(hexid(), hexid(), 0, 0, 320, 0)  # height fixed in render()
        self.top_items.append(
            f'<item id="{self.boundary.id}" cid="{cid("SYS")}" type="system-boundary" '
            f'name="{esc(boundary_name)}" creator="" creation-date="{now()}"><owned-items /></item>'
        )

    def add_actor(self, name):
        node = Node(hexid(), hexid(), -220, 40 + 160 * len(self.actors), 50, 120)
        self.top_items.append(
            f'<item id="{node.id}" cid="{cid("AC")}" type="actor" name="{esc(name)}" '
            f'creation-date="{now()}" visibility="undefined" />'
        )
        self._place(node, body="<actor />",
                    layout='name-position="0,10" name-anchor="bottom" auto-anchor="true" label-attached="false" ')
        self.actors[name] = node
        return node.id

    def add_usecase(self, name):
        node = Node(hexid(), hexid(), 60, 20 + 90 * len(self.usecases), 200, 50)
        self.top_items.append(
            f'<item id="{node.id}" cid="{cid("UC")}" type="use-case" name="{esc(name)}" owner="{self.boundary.id}" '
            f'creation-date="{now()}" visibility="undefined">'
            f'<use-case><stakeholders /><special-requirements /><issues /></use-case></item>'
        )
        self._place(node, container=self.boundary, body="<use-case />")
        self.usecases[name] = node
        return node.id

    def add_association(self, actor, usecase):
        return self._association(self.actors[actor], self.usecases[usecase])

    def add_include(self, from_uc, to_uc):
        return self._stereotyped("include", "INC", from_uc, to_uc)

    def add_extend(self, from_uc, to_uc):
        return self._stereotyped("extend", "EX", from_uc, to_uc, '<extend extension-point="" condition="" />')

    def _stereotyped(self, kind, prefix, from_uc, to_uc, extra=""):
        a, b = self.usecases[from_uc], self.usecases[to_uc]
        rid = hexid()
        self.abstract_items.append(
            f'<item id="{rid}" cid="{cid(prefix)}" type="{kind}" owner="{self.boundary.id}" creator="" '
            f'creation-date="{now()}" from="{a.id}" to="{b.id}" visibility="package">'
            f'<stereotypes><stereotype name="{kind}" /></stereotypes>'
            f'<stereotype-instances><stereotype id="{rid}_{kind}_c" type="{kind}" '
            f'creation-date="{now()}" ref="" /></stereotype-instances>{extra}</item>'
        )
        self._connect(rid, a, b)
        return rid

    def render(self, order_index=1):
        # boundary goes first in the layer so use cases draw on top
        height = max([n.y for n in self.usecases.values()] + [100]) + 85
        self._place(self.boundary._replace(h=height))
        self.layer_items.insert(0, self.layer_items.pop())
        return super().render(order_index)


class SequenceDiagram(Diagram):
    """Lifelines, call/reply messages (fresh activation bar each), loop/opt fragments.
    No `alt`: unconfirmed, use two `opt` blocks."""

    TYPE = "uml-sequence"
    SPACING = 220

    def __init__(self, name, actors=None):
        super().__init__(name)
        self.actors = actors or {}  # name -> Node, from UseCaseDiagram.actors
        self.lifelines = {}         # name -> Node
        self._y = 60                # next message row
        self._fragments = []        # open fragments: (id, start_y)

    def add_lifeline(self, name):
        if name in self.actors:
            lid = self.actors[name].id  # already declared; reference only
        else:
            lid = hexid()
            self.abstract_items.append(
                f'<item id="{lid}" cid="{cid("LL")}" type="lifeline" name="{esc(name)}" creation-date="{now()}" '
                f'visibility="undefined"><owned-items /><lifeline classifier-name="" selector="" '
                f'is-multi-object="false" /></item>'
            )
        node = Node(lid, hexid(), self.SPACING * len(self.lifelines), 17, 140, 700)
        self._place(node, kind="lifeline", padded=True)
        self.lifelines[name] = node
        return lid

    def _activation_bar(self, lifeline, y):
        ll = self.lifelines[lifeline]
        c = cid("ES")
        bar = Node(hexid(), hexid(), ll.x + 60, y, 20, 40)
        self.abstract_items.append(
            f'<item id="{bar.id}" cid="{c}" name="ExecutionSpecification{c[2:]}" '
            f'type="activation-bar" owner="{ll.id}" creator="" creation-date="{now()}">'
            f'<activation-bar lifeline-ref="{ll.id}" /></item>'
        )
        self._place(bar, container=ll, padded=True)
        return bar

    def add_message(self, from_ll, to_ll, kind, label):
        """kind: 'call' or 'reply'."""
        y = self._y
        self._y += 85
        a = self._activation_bar(from_ll, y)
        b = a if from_ll == to_ll else self._activation_bar(to_ll, y)
        c = cid("SM")
        mid = hexid()
        self.abstract_items.append(
            f'<item id="{mid}" cid="{c}" name="Message{c[2:]}" type="sequence-action" '
            f'creator="" creation-date="{now()}" from="{a.id}" to="{b.id}" visibility="package">'
            f'<sequence-action type="{kind}" message="{esc(label)}" is-asynchronous="false" return-value="" '
            f'assign-to-variable=""><parameters /></sequence-action></item>'
        )
        self.layer_items.append(
            f'<item id="{mid}" iid="{hexid()}" creation-date="{now()}" order-index="0" type="relation">'
            f'<layout message-x="{min(a.x, b.x) + 40}" message-y="{y}" line-style="oblique" lock-start-point="true" '
            f'lock-end-point="true" start-absolute-lock="true" end-absolute-lock="true" lock-to-fields="false" '
            f'auto-path="" x1="{a.x}" y1="{y}" x2="{b.x}" y2="{y}" start-border-pos="0.25" end-border-pos="0.99" '
            f'start-local-pos="0" end-local-pos="0" name-position="0,20">'
            f'<points><point x="{a.x}" y="{y}" /><point x="{b.x}" y="{y}" /></points></layout>'
            f'<relation from="{a.id}" from-iid="{a.iid}" to="{b.id}" to-iid="{b.iid}" />'
            f'<sequence-action show-sequence-number="false" /></item>'
        )
        return mid

    def start_fragment(self, operator, label):
        """operator: 'loop' or 'opt'. Pair with end_fragment()."""
        fid = hexid()
        self.abstract_items.append(
            f'<item id="{fid}" cid="{cid("FR")}" name="{esc(label)}" type="fragment" creator="" creation-date="{now()}">'
            f'<fragment operator="{operator}"><operands /></fragment></item>'
        )
        self._fragments.append((fid, self._y))
        self._y += 20
        return fid

    def end_fragment(self):
        fid, start = self._fragments.pop()
        self._y += 20
        width = max(self.SPACING * len(self.lifelines), 400)
        self._place(Node(fid, hexid(), -20, start, width, self._y - start), padded=True)


class ClassDiagram(Diagram):
    """Packages, classes (typed attributes/operations), associations, generalizations,
    dependencies. Doubles as package diagram: SIM draws packages on a class canvas."""

    TYPE = "uml-class"

    def __init__(self, name):
        super().__init__(name)
        self.packages = {}  # name -> Node
        self.classes = {}   # name -> Node
        self._pkg_y = {}    # package name -> next free y

    def add_package(self, name, width=340, height=560):
        node = Node(hexid(), hexid(), 40 + sum(p.w + 100 for p in self.packages.values()), 40, width, height)
        self.top_items.append(
            f'<item id="{node.id}" cid="{cid("PKG")}" type="package" name="{esc(name)}" creator="" '
            f'creation-date="{now()}"><owned-items /></item>'
        )
        self._place(node, body='<package name-in-body="false" />',
                    layout=f'expanded="{node.x},{node.y},{node.w},{node.h}" collapsed="0,0,0,0" ')
        self.packages[name] = node
        self._pkg_y[name] = node.y + 50
        return node.id

    def add_class(self, name, package=None, attributes=(), operations=(), width=280, height=None):
        """attributes: [(name, type)]; operations: [(name, return_type, [(param, type)])].
        Types are TYPE_MAP keys or None."""
        cls_id = hexid()
        attrs = ""
        for attr, key in attributes:
            pid = hexid()
            pcid = cid("PROP")
            tname, tid = _type(key)
            feature = f'<structural-feature type="{tname}" type-id="{tid}" />' if tname else ""
            self.top_items.append(
                f'<item id="{pid}" cid="{pcid}" type="property" name="{esc(attr)}" owner="{cls_id}" creator="" '
                f'creation-date="{now()}" visibility="private">{feature}<property /></item>'
            )
            attrs += (f'<attribute id="a{hexid()}" cid="{pcid}" name="{esc(attr)}" '
                      f'creation-date="{now()}" property-ref="{pid}" />')
        ops = ""
        for op, ret_key, params in operations:
            rname, rid = _type(ret_key)
            plist = "".join(
                f'<parameter id="p{hexid()}" name="{esc(p)}" type="{_type(k)[0]}" type-id="{_type(k)[1]}" '
                f'creation-date="{now()}" />' for p, k in params or ()
            )
            ops += (
                f'<operation id="o{hexid()}" cid="{cid("OP")}" name="{esc(op)}" creation-date="{now()}" '
                f'type="{rname}" type-id="{rid}" visibility="public">'
                f'{"<parameters>" + plist + "</parameters>" if plist else ""}'
                f'<source-codes><source-code language="Java" /></source-codes></operation>'
            )
        pkg = self.packages.get(package)
        owner = f' owner="{pkg.id}"' if pkg else ""
        self.top_items.append(
            f'<item id="{cls_id}" cid="{cid("C")}" type="class" name="{esc(name)}"{owner} creator="" '
            f'creation-date="{now()}"><owned-items />'
            f'{"<attributes>" + attrs + "</attributes>" if attrs else ""}'
            f'{"<operations>" + ops + "</operations>" if ops else ""}'
            f'<source-codes><source-code language="Java" /></source-codes></item>'
        )
        height = height or 70 + 22 * (len(attributes) + len(operations))
        if pkg:
            node = Node(cls_id, hexid(), pkg.x + 30, self._pkg_y[package], width, height)
            self._pkg_y[package] += height + 30
        else:
            node = Node(cls_id, hexid(), 40, 40, width, height)
        self._place(node, container=pkg, attrs=' show-fields="true"', body="<classifier /><class />")
        self.classes[name] = node
        return cls_id

    def _node(self, name):
        return self.classes.get(name) or self.packages[name]

    def _simple_relation(self, kind, prefix, from_name, to_name, label=None):
        """Relation without role ends (generalization, dependency)."""
        a, b = self._node(from_name), self._node(to_name)
        rid = hexid()
        name = f' name="{esc(label)}"' if label else ""
        self.abstract_items.append(
            f'<item id="{rid}" cid="{cid(prefix)}" type="{kind}" creator=""{name} creation-date="{now()}" '
            f'from="{a.id}" to="{b.id}" visibility="package" />'
        )
        self._connect(rid, a, b)
        return rid

    def add_generalization(self, child, parent):
        return self._simple_relation("generalization", "GNR", child, parent)

    def add_dependency(self, client, supplier, label=None):
        """Between classes or between packages."""
        return self._simple_relation("dependency", "DEP", client, supplier, label)

    def add_association(self, a, b, label=None):
        return self._association(self._node(a), self._node(b), label=label)


class ActivityDiagram(Diagram):
    """Initial, action, decision, final nodes joined by labeled flows."""

    TYPE = "uml-activity"
    _DOT = 'name-position="0,10" name-anchor="bottom" auto-anchor="true" label-attached="false" '

    def __init__(self, name):
        super().__init__(name)
        self.nodes = {}  # id -> Node

    def _node(self, kind, prefix, x, y, w, h, name=None, layout="", body=""):
        node = Node(hexid(), hexid(), x, y, w, h)
        label = f' name="{esc(name)}"' if name else ""
        inner = f">{body}</item>" if body else " />"
        self.top_items.append(
            f'<item id="{node.id}" cid="{cid(prefix)}" type="{kind}"{label} creator="" creation-date="{now()}"{inner}'
        )
        self._place(node, layout=layout)
        self.nodes[node.id] = node
        return node.id

    def add_initial(self, x, y):
        return self._node("initial-node", "IN", x, y, 25, 25, layout=self._DOT)

    def add_final(self, x, y):
        return self._node("activity-final-node", "AFN", x, y, 25, 25, layout=self._DOT)

    def add_action(self, label, x, y, w=260, h=50):
        return self._node("action", "ACT", x, y, w, h, label, body='<action locally-reentrant="false" />')

    def add_decision(self, label, x, y, w=90, h=98):
        return self._node("decision", "DC", x, y, w, h, label,
                          layout='name-position="1.5,-1" name-anchor="toelement" name-width="98" '
                                 'auto-anchor="true" label-attached="false" ')

    def add_flow(self, from_id, to_id, label=None):
        a, b = self.nodes[from_id], self.nodes[to_id]
        if abs(a.center[1] - b.center[1]) < 20:   # same row: side to side
            p1, p2 = (a.x + a.w, a.center[1]), (b.x, b.center[1])
        else:                                     # bottom to top
            p1, p2 = (a.center[0], a.y + a.h), (b.center[0], b.y)
        rid = hexid()
        name = f' name="{esc(label)}"' if label else ""
        self.abstract_items.append(
            f'<item id="{rid}" cid="{cid("ELEM")}"{name} type="universal-connector" creator="" '
            f'creation-date="{now()}" from="{a.id}" to="{b.id}"><connector end-cap="arrow" /></item>'
        )
        self._connect(rid, a, b, p1, p2)
        return rid


class SimProjectFile:
    """<sim-project> envelope. add() diagrams in order, then write()."""

    def __init__(self, name, author):
        self.name, self.author = esc(name), esc(author)
        self.items = []
        self.diagrams = []

    def add(self, diagram):
        self.diagrams.append(diagram.render(len(self.diagrams) + 1))
        self.items.extend(diagram.top_items)

    def write(self, path):
        Path(path).write_text(self.render(), encoding="utf-8")

    def render(self):
        return f'''<?xml version="1.0" encoding="utf-8" standalone="yes"?>
<sim-project version="15.21" multi-file="no" uid="simp{hexid()}" creation-date="{now()}">
  <meta><name>{self.name}</name><authors>{self.author}</authors><description /></meta>
  <counters models="1"><entity-names /><entity-ids /><diagrams /><fields /></counters>
  <alias-groups />
  <management uid="md-{hexid()}" name="" task-id-sequence="0">
    <persons><person id=""><first-name>{self.author}</first-name><last-name /><role /><e-mail />
      <phone-number /><description /><color>#00000000</color></person></persons>
    <teams /><sprints /><projects /><modules /><tasks /><to-dos />
  </management>
  <glossary id="glsr-{hexid()}" name="" order-index="-1" />
  <types default="Java">
    <type-sets><type-set file="JavaTypes.xml" /><type-set file="UmlTypes.xml" /></type-sets>
    <custom-types><parameters /><types /></custom-types>
  </types>
  <items>{"".join(self.items)}</items>
  <models>
    <model id="p{hexid()}" name="Model1" namespace="" order-index="1" expanded="true">
      {meta("01/01/0001 00:00:00")}
      <abstract-items /><sub-models />
      {"".join(self.diagrams)}
    </model>
  </models>
</sim-project>'''
