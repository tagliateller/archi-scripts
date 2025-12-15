#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Generate a large ArchiMate Model Exchange (Open Group AMEFF) XML file for import into Archi.

Key compatibility rules for Archi's AMEFF importer:
- Use default namespace: http://www.opengroup.org/xsd/archimate/3.0/
- Use unprefixed xsi:type values, e.g. xsi:type="Device", xsi:type="CompositionRelationship"
  (NOT "archimate:Device", NOT "archimate:CompositionRelationship")
- Use CommunicationNetwork (not "Network")
"""

from __future__ import annotations

import argparse
import datetime as dt
import xml.etree.ElementTree as ET
from typing import List

ARCH_NS = "http://www.opengroup.org/xsd/archimate/3.0/"
XSI_NS = "http://www.w3.org/2001/XMLSchema-instance"
DC_NS = "http://purl.org/dc/elements/1.1/"

ET.register_namespace("", ARCH_NS)
ET.register_namespace("xsi", XSI_NS)
ET.register_namespace("dc", DC_NS)


def q(tag: str) -> str:
    return f"{{{ARCH_NS}}}{tag}"


def make_element(parent: ET.Element, identifier: str, element_type: str, name_de: str) -> ET.Element:
    el = ET.SubElement(parent, q("element"), {
        "identifier": identifier,
        f"{{{XSI_NS}}}type": element_type,   # IMPORTANT: unprefixed type value
    })
    nm = ET.SubElement(el, q("name"), {"{http://www.w3.org/XML/1998/namespace}lang": "de"})
    nm.text = name_de
    return el


def add_property(el: ET.Element, prop_def_ref: str, value: str) -> None:
    props = el.find(q("properties"))
    if props is None:
        props = ET.SubElement(el, q("properties"))
    prop = ET.SubElement(props, q("property"), {"propertyDefinitionRef": prop_def_ref})
    val = ET.SubElement(prop, q("value"), {"{http://www.w3.org/XML/1998/namespace}lang": "de"})
    val.text = value


def make_relationship(
    parent: ET.Element,
    identifier: str,
    rel_type: str,
    source: str,
    target: str,
    name_de: str | None = None
) -> ET.Element:
    rel = ET.SubElement(parent, q("relationship"), {
        "identifier": identifier,
        f"{{{XSI_NS}}}type": rel_type,       # IMPORTANT: unprefixed type value
        "source": source,
        "target": target,
    })
    if name_de:
        nm = ET.SubElement(rel, q("name"), {"{http://www.w3.org/XML/1998/namespace}lang": "de"})
        nm.text = name_de
    return rel


def build_model(
    n_servers: int,
    n_k8s_clusters: int,
    k8s_workers_per_cluster: int,
    output_path: str
) -> None:
    # For Archi AMEFF import, Diagram XSD is commonly used in schemaLocation examples
    schema_location = (
        f"{ARCH_NS} {ARCH_NS}archimate3_Diagram.xsd "
        f"{DC_NS} http://dublincore.org/schemas/xmls/qdc/2008/02/11/dc.xsd"
    )

    model = ET.Element(q("model"), {
        "identifier": "id-model-dc-large",
        f"{{{XSI_NS}}}schemaLocation": schema_location,
    })

    name = ET.SubElement(model, q("name"), {"{http://www.w3.org/XML/1998/namespace}lang": "de"})
    name.text = "Beispiel: Großes Rechenzentrum (Server + Kubernetes) – generiert"

    doc = ET.SubElement(model, q("documentation"), {"{http://www.w3.org/XML/1998/namespace}lang": "de"})
    doc.text = (
        f"Generiertes Beispielmodell mit {n_servers} Servern und {n_k8s_clusters} Kubernetes-Clustern "
        f"(Workers/Cluster={k8s_workers_per_cluster}). Erzeugt am {dt.datetime.now().isoformat(timespec='seconds')}."
    )

    elements = ET.SubElement(model, q("elements"))
    relationships = ET.SubElement(model, q("relationships"))

    # ---- Core
    id_loc = "id-loc-dc1"
    make_element(elements, id_loc, "Location", "Rechenzentrum DC1")

    # ---- Services
    id_svc_portfolio = "id-techsvc-portfolio"
    el_portfolio = make_element(elements, id_svc_portfolio, "TechnologyService", "Service-Portfolio (250 Services)")
    add_property(el_portfolio, "pd-count", "250")

    id_svc_k8s = "id-techsvc-k8s"
    make_element(elements, id_svc_k8s, "TechnologyService", "Containerplattform (Kubernetes)")

    # ---- Networks / VLANs (FIX: CommunicationNetwork)
    id_net_core = "id-net-core"
    id_vlan_server = "id-vlan20-server"
    id_vlan_mgmt = "id-vlan30-mgmt"

    make_element(elements, id_net_core, "CommunicationNetwork", "Core Netzwerk")
    make_element(elements, id_vlan_server, "CommunicationNetwork", "VLAN 20 – Server")
    make_element(elements, id_vlan_mgmt, "CommunicationNetwork", "VLAN 30 – Management")

    make_relationship(relationships, "r-loc-contains-core", "Composition", id_loc, id_net_core)
    make_relationship(relationships, "r-core-agg-vlan20", "Aggregation", id_net_core, id_vlan_server)
    make_relationship(relationships, "r-core-agg-vlan30", "Aggregation", id_net_core, id_vlan_mgmt)

    # ---- Servers
    server_ids: List[str] = []
    for i in range(1, n_servers + 1):
        sid = f"id-dev-srv-{i:04d}"
        server_ids.append(sid)

        srv = make_element(elements, sid, "Device", f"Server {i:04d}")
        add_property(srv, "pd-tech", "x86_64, Linux" if i % 2 == 0 else "x86_64, Windows")

        # Simple connectivity modelling:
        make_relationship(relationships, f"r-srv-{i:04d}-vlan", "Association", sid, id_vlan_server)
        make_relationship(relationships, f"r-srv-{i:04d}-portfolio", "Realization", sid, id_svc_portfolio)

    # ---- Kubernetes clusters + optional workers
    cluster_ids: List[str] = []
    worker_ids: List[str] = []

    for c in range(1, n_k8s_clusters + 1):
        cid = f"id-node-k8s-cluster-{c:03d}"
        cluster_ids.append(cid)

        cl = make_element(elements, cid, "Node", f"Kubernetes Cluster {c:03d}")
        add_property(cl, "pd-tech", "Kubernetes")

        make_relationship(relationships, f"r-k8s-{c:03d}-realize", "Realization", cid, id_svc_k8s)
        make_relationship(relationships, f"r-k8s-{c:03d}-core", "Association", cid, id_net_core)

        for w in range(1, k8s_workers_per_cluster + 1):
            wid = f"id-dev-k8s-worker-{c:03d}-{w:03d}"
            worker_ids.append(wid)

            wk = make_element(elements, wid, "Device", f"K8s Worker {c:03d}-{w:03d}")
            add_property(wk, "pd-tech", "Linux Worker Node")

            make_relationship(relationships, f"r-wk-{c:03d}-{w:03d}-cluster", "Association", wid, cid)
            make_relationship(relationships, f"r-wk-{c:03d}-{w:03d}-vlan", "Association", wid, id_vlan_server)

    # ---- Organization folder (optional, but Archi imports it fine)
    orgs = ET.SubElement(model, q("organizations"))
    folder = ET.SubElement(orgs, q("item"))
    folder_name = ET.SubElement(folder, q("label"), {"{http://www.w3.org/XML/1998/namespace}lang": "de"})
    folder_name.text = "Technology"

    def add_ref(ref_id: str) -> None:
        ET.SubElement(folder, q("item"), {"identifierRef": ref_id})

    for ref in [id_loc, id_svc_portfolio, id_svc_k8s, id_net_core, id_vlan_server, id_vlan_mgmt]:
        add_ref(ref)
    for sid in server_ids:
        add_ref(sid)
    for cid in cluster_ids:
        add_ref(cid)
    for wid in worker_ids:
        add_ref(wid)

    # ---- Property definitions
    prop_defs = ET.SubElement(model, q("propertyDefinitions"))

    def propdef(pid: str, pname: str) -> None:
        pd = ET.SubElement(prop_defs, q("propertyDefinition"), {"identifier": pid, "type": "string"})
        nm = ET.SubElement(pd, q("name"), {"{http://www.w3.org/XML/1998/namespace}lang": "de"})
        nm.text = pname

    propdef("pd-count", "count")
    propdef("pd-tech", "technology")

    tree = ET.ElementTree(model)
    ET.indent(tree, space="  ", level=0)
    tree.write(output_path, encoding="utf-8", xml_declaration=True)

    print(f"Wrote: {output_path}")
    print(f"Servers: {n_servers}, K8s clusters: {n_k8s_clusters}, K8s workers total: {len(worker_ids)}")


def main() -> None:
    ap = argparse.ArgumentParser(description="Generate large AMEFF (ArchiMate Exchange) XML for Archi import.")
    ap.add_argument("--servers", type=int, default=1000)
    ap.add_argument("--k8s-clusters", type=int, default=20)
    ap.add_argument("--k8s-workers-per-cluster", type=int, default=0)
    ap.add_argument("--out", type=str, default="dc_archimate_large_v2.xml")
    args = ap.parse_args()

    if args.servers < 1:
        raise SystemExit("ERROR: --servers must be >= 1")
    if args.k8s_clusters < 1:
        raise SystemExit("ERROR: --k8s-clusters must be >= 1")
    if args.k8s_workers_per_cluster < 0:
        raise SystemExit("ERROR: --k8s-workers-per-cluster must be >= 0")

    build_model(args.servers, args.k8s_clusters, args.k8s_workers_per_cluster, args.out)


if __name__ == "__main__":
    main()

