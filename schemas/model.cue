package atlas

import "list"

// Authoring types. Definitions are closed: misspelled/unknown fields fail.
#Text:        string & =~"\\S"
#Path:        #Text & !~"^/" & !~"[:?#\\\\]" & !~"(^|/)\\.\\.?(/|$)"
#Version:     #Text
#SystemID:    string & =~"^SYS-[A-Za-z0-9-]+$"
#ComponentID: string & =~"^CMP-[A-Za-z0-9-]+$"
#InterfaceID: string & =~"^IF-[A-Za-z0-9-]+$"
#ContractID:  string & =~"^DC-[A-Za-z0-9-]+$"
#ViewID:      string & =~"^VIEW-[A-Za-z0-9-]+$"
#StepID:      string & =~"^[a-z][a-z0-9-]*$"
#EntityRef: {kind: "system", id: #SystemID} | {kind: "component", id: #ComponentID}
#InterfaceRef: {id: #InterfaceID, version: #Version}
#ContractRef: {id: #ContractID, version: #Version}
#Artifact: {label: #Text, kind: "openapi" | "xsd" | "markdown" | "other", path: #Path}
#LinkTarget: #EntityRef |
	{kind: "interface", id: #InterfaceID} |
	{kind: "dataContract", id: #ContractID} |
	{kind: "view", id: #ViewID} |
	{kind: "file", path: #Path}
#Annotation: {text: #Text, links: *[] | [...{label: #Text, target: #LinkTarget}]}
#System: {id: #SystemID, name: #Text, description: #Text, boundary: "internal" | "external"}
#Component: {id: #ComponentID, name: #Text, description: #Text, systemId: #SystemID}
#Interface: {
	id:          #InterfaceID
	name:        #Text
	description: #Text
	owner:       #EntityRef
	protocol:    #Text
	versions: [string]: {
		artifacts: [#Artifact, ...#Artifact]
		// Capability declarations, not actual consumers or routes.
		envelopes?: [string]: [#Version, ...#Version]
	}
}
#DataContract: {
	id:          #ContractID
	name:        #Text
	description: #Text
	versions: [string]: {artifacts: [#Artifact, ...#Artifact]}
}
#Transport: {
	viaInterface: #InterfaceRef
	envelope:     #ContractRef
	// Make envelope placement a deliberate authoring choice.
	envelopeScope: "router-leg" | "end-to-end"
}
#Step: {
	id:         #StepID
	annotation: #Annotation
	if kind != "response" {
		kind:        "request" | "event"
		participant: #EntityRef
		interface:   #InterfaceRef
		transport?:  #Transport
	}
	if kind == "response" {
		kind:       "response"
		responseTo: #StepID
	}
	kind: "request" | "event" | "response"
}
#View: {
	id:          #ViewID
	name:        #Text
	description: #Text
	kind:        "scenario" | "overview"
	if kind == "scenario" {steps: [#Step, ...#Step]}

	// Overviews project scenario usages; they do not copy connections.
	if kind == "overview" {scenarios: [#ViewID, ...#ViewID]}
}

#Model: {
	systems: [ID=string]: #System & {id: ID}
	components: [ID=string]: #Component & {id: ID}
	interfaces: [ID=string]: #Interface & {id: ID}
	dataContracts: [ID=string]: #DataContract & {id: ID}
	views: [ID=string]: #View & {id: ID}
	// Filesystem facts supplied by the loader; all relationship rules stay here.
	files: [string]: {version?: string}
	let systemIDs = [for id, _ in systems {id}]
	let componentIDs = [for id, _ in components {id}]
	let interfaceIDs = [for id, _ in interfaces {id}]
	let contractIDs = [for id, _ in dataContracts {id}]
	let viewIDs = [for id, _ in views {id}]
	let entityIDs = list.Concat([systemIDs, componentIDs])
	let filePaths = [for path, _ in files {path}]

	// Hidden computed assertions are evaluated by cue export but not emitted.
	_checks: {
		componentChecks: {for id, c in components {(id): true & list.Contains(systemIDs, c.systemId)}}
		interfaceChecks: {
			for id, iface in interfaces {
				(id): {
					owner:    true & list.Contains(entityIDs, iface.owner.id)
					versions: true & (len(iface.versions) > 0)
					artifacts: [for version, value in iface.versions for artifact in value.artifacts {
						present: true & list.Contains(filePaths, artifact.path)
						if artifact.kind == "openapi" || artifact.kind == "xsd" {
							versionMatches: true & (files[artifact.path].version == version)
						}
					}]
					envelopes: [for _, value in iface.versions if value.envelopes != _|_ for contract, versions in value.envelopes {
						known: true & list.Contains(contractIDs, contract)
						versions: [for version in versions {true & list.Contains([for v, _ in dataContracts[contract].versions {v}], version)}]
					}]
				}
			}
		}
		contractChecks: {
			for id, contract in dataContracts {
				(id): {
					versions: true & (len(contract.versions) > 0)
					artifacts: [for version, value in contract.versions for artifact in value.artifacts {
						present: true & list.Contains(filePaths, artifact.path)
						if artifact.kind == "openapi" || artifact.kind == "xsd" {
							versionMatches: true & (files[artifact.path].version == version)
						}
					}]
				}
			}
		}
		viewChecks: {
			for viewID, view in views {
				(viewID): {
					if view.kind == "overview" {
						unique: true & list.UniqueItems(view.scenarios)
						scenarios: [for id in view.scenarios {
							known: true & list.Contains(viewIDs, id)
							kind:  true & (views[id].kind == "scenario")
						}]
					}
					if view.kind == "scenario" {
						uniqueSteps: true & list.UniqueItems([for step in view.steps {step.id}])
						steps: {
							for index, step in view.steps {
								(step.id): {
									if step.kind == "response" {
										originalRequest: true & list.Contains([for i, previous in view.steps if i < index && previous.kind == "request" {previous.id}], step.responseTo)
									}
									if step.kind != "response" {
										participant: true & list.Contains(entityIDs, step.participant.id)
										interface:   true & list.Contains(interfaceIDs, step.interface.id)
										version: true & list.Contains([for v, _ in interfaces[step.interface.id].versions {v}], step.interface.version)
										distinctEndpoints: true & (step.participant.id != interfaces[step.interface.id].owner.id)
										if step.transport != _|_ {
											let route = step.transport
											routingInterface: true & list.Contains(interfaceIDs, route.viaInterface.id)
											routingVersion: true & list.Contains([for v, _ in interfaces[route.viaInterface.id].versions {v}], route.viaInterface.version)
											contract: true & list.Contains(contractIDs, route.envelope.id)
											contractVersion: true & list.Contains([for v, _ in dataContracts[route.envelope.id].versions {v}], route.envelope.version)
											supportedEnvelope: true & list.Contains(interfaces[route.viaInterface.id].versions[route.viaInterface.version].envelopes[route.envelope.id], route.envelope.version)
											distinctRouter:    true & (interfaces[route.viaInterface.id].owner.id != step.participant.id) & (interfaces[route.viaInterface.id].owner.id != interfaces[step.interface.id].owner.id)
										}
									}
									links: [for link in step.annotation.links {
										let target = link.target
										if target.kind == "system" {known: true & list.Contains(systemIDs, target.id)}
										if target.kind == "component" {known: true & list.Contains(componentIDs, target.id)}
										if target.kind == "interface" {known: true & list.Contains(interfaceIDs, target.id)}
										if target.kind == "dataContract" {known: true & list.Contains(contractIDs, target.id)}
										if target.kind == "view" {known: true & list.Contains(viewIDs, target.id)}
										if target.kind == "file" {known: true & list.Contains(filePaths, target.path)}
									}]
								}
							}
						}
					}
				}
			}
		}
	}
}
