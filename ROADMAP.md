# TUC Roadmap

## Zielbild

TUC, der Triton Universal Compiler, soll KI-Entwicklern erlauben, mathematische Kernels einmal zu schreiben und sie auf unterschiedlichen Beschleunigern auszufuehren: NVIDIA/AMD-GPUs zuerst, danach photonische, neuromorphe und weitere spezialisierte Hardware.

Der entscheidende Gedanke ist nicht, sofort jede Hardware zu unterstuetzen. Der erste Beweis muss sein:

- Bestehende Triton-Kernels laufen weiter.
- Die Compiler-Pipeline kann eine hardwareagnostische Zwischenform ausdruecken.
- Backends koennen als Plugins angebunden werden.
- Ein Runtime-System kann Arbeit sinnvoll zwischen mehreren Geraeten aufteilen.
- Rauschen, Kalibrierung und physikalische Constraints werden als Compiler- und Runtime-Daten modelliert.

## Strategischer MVP

Der MVP sollte kein vollstaendiger Universal-Compiler sein. Er sollte ein glaubwuerdiger, messbarer Vertical Slice sein:

1. Ein kleiner Satz realer Triton-Kernels: MatMul, Elementwise, Reduction, Softmax-nahe Patterns.
2. Eine MLIR-basierte Pipeline mit drei klaren Ebenen: TLIR, HAC-IR, HS-IR.
3. Bestehende GPU-Ausgabe bleibt kompatibel und performant genug.
4. Eine Backend-API kann ein simuliertes Spezialgeraet anbinden.
5. Ein Noise-Aware-Tuning-Prototyp zeigt, dass TUC nicht nur Geschwindigkeit, sondern Robustheit optimieren kann.
6. Eine einfache Runtime partitioniert einen kleinen Graphen zwischen GPU und Spezialbackend.

Damit entsteht frueh ein sichtbarer Beweis: "TUC kann existierenden Triton-Code nehmen, ihn durch eine neue IR-Schicht fuehren und Teile davon auf ein nicht-traditionelles Backend mappen."

## Nicht-Ziele Fuer Version 1

- Kein sofortiger Support fuer beliebige PyTorch-Modelle.
- Kein echter Quanten-Hybrid-Backend im ersten Jahr.
- Keine komplette Neuimplementierung von Triton.
- Keine perfekte Performance-Paritaet fuer alle Kernels.
- Keine vollautomatische Modellpartitionierung ohne explizite Kostenmodelle.

Diese Begrenzungen sind wichtig, damit die Vision gross bleibt, aber die Umsetzung nicht zerfasert.

## Architektur-Arbeitsstraenge

### 1. Frontend Und Developer Experience

Ziel: Entwickler schreiben weiterhin vertraute Triton-nahe Python-Kernels.

Aufgaben:

- Bestehende `@triton.jit`-Semantik analysieren und Kompatibilitaetsmatrix erstellen.
- Neue optionale Hints definieren, zum Beispiel `robust_to_noise`, `prefer_sparsity`, `prefer_analog_linear`, `max_error_budget`.
- Hints zuerst als Metadaten durch die Pipeline tragen, ohne Verhalten zu aendern.
- Fehlerausgaben und Debug-Views bauen: "Warum wurde dieser Kernel so partitioniert?"
- Golden-Kernel-Suite fuer typische AI-Workloads aufbauen.

Meilenstein:

- Ein Entwickler kann einen bestehenden Triton-Kernel mit TUC kompilieren, Hints setzen und die transformierte IR inspizieren.

### 2. MLIR Pipeline

Ziel: Eine robuste, erweiterbare Compiler-Pipeline, die nicht an eine einzelne Hardwarearchitektur gebunden ist.

Ebenen:

- TLIR: Triton-nahe High-Level-Darstellung.
- HAC-IR: Hardware-Agnostic Compute IR fuer fundamentale Operationen und Constraints.
- HS-IR: Hardware-Specific IR fuer konkrete Zielgeraete.

Aufgaben:

- Minimalen HAC-IR-Dialekt definieren: Tensor-Operationen, lineare Algebra, Reduktionen, Elementwise-Operationen, Fehlerbudgets, Datenbewegung.
- Lowering von TLIR zu HAC-IR fuer die MVP-Kernels bauen.
- Lowering von HAC-IR zu GPU-HS-IR bauen.
- Pass-Infrastruktur fuer Pattern-Rewrites, Fusion, Partitionierung und Kostenmodell-Anbindung aufsetzen.
- IR-Printer und Visualisierung fuer Debugging bereitstellen.

Meilenstein:

- MatMul und Elementwise-Kernels koennen von TLIR zu HAC-IR und zurueck in ein funktionierendes GPU-Backend laufen.

### 3. Backend API

Ziel: Hardware-Hersteller sollen ein Backend schreiben koennen, ohne die ganze Compiler-Pipeline zu verstehen.

Aufgaben:

- Capability-Modell definieren: unterstuetzte Ops, Speicherformate, Latenzmodell, Bandbreite, Fehlerprofil, Kalibrierungsbedarf.
- Backend-Vertrag definieren: Input HS-IR, Output Code/Config/Runtime-Plan.
- Plugin-Lifecycle definieren: Registrierung, Feature Discovery, Validierung, Versionierung.
- Referenzbackend bauen: CPU- oder Simulator-Backend als einfaches Beispiel.
- Documentation-first API: Ein Backend-Autor muss innerhalb weniger Tage einen Toy-Backend anbinden koennen.

Meilenstein:

- Ein externes Beispielbackend kann eine lineare Operation akzeptieren, kompilieren und ueber die Runtime ausfuehren.

### 4. GPU Legacy Backends

Ziel: Vertrauen gewinnen, indem existierende NVIDIA/AMD-Faehigkeiten erhalten bleiben.

Aufgaben:

- Bestehende Triton-GPU-Pipeline respektieren und nur gezielt erweitern.
- PTX/NVIDIA- und AMD/HIP-Pfade als Baseline behalten.
- Benchmark-Suite gegen Triton, cuBLAS/rocBLAS und relevante Kernel-Baselines aufbauen.
- Auto-Tuning nicht neu erfinden, sondern bestehende Mechanismen integrieren.
- Performance-Regressions frueh in CI sichtbar machen.

Meilenstein:

- Fuer MVP-Kernels liegt TUC auf GPU innerhalb eines definierten Performance-Fensters zur Triton-Baseline, zum Beispiel 90 bis 100 Prozent je nach Kerneltyp.

### 5. Photonik-Referenzbackend

Ziel: Den radikalen Teil des Konzepts beweisen, ohne direkt von realem Silizium abzuhaengen.

Aufgaben:

- Photonik-Simulator bauen oder integrieren: MZI-Matrixmodell, ADC/DAC-Grenzen, thermisches Rauschen, Kalibrierungsparameter.
- HAC-IR-Patterns erkennen, die linear-analog abbildbar sind.
- Nicht-lineare Operationen automatisch an digitale Hardware delegieren.
- Runtime-Plan erzeugen: Analog-Teil, digitale Nachbearbeitung, Datenbewegung.
- Thermal-Tuning/Calibration als explizite Runtime-Schritte modellieren.

Meilenstein:

- Ein kleiner Attention- oder MLP-Block wird zwischen GPU und photonischem Simulator partitioniert, mit messbarem Genauigkeits-/Robustheitsbericht.

### 6. Neuromorphes Referenzbackend

Ziel: Eine zweite nicht-traditionelle Klasse testen, um zu beweisen, dass HAC-IR nicht nur "Photonik plus GPU" ist.

Aufgaben:

- Sparse Connectivity als Zielmodell definieren.
- Dichte Gewichte in sparse, gewichtete Verbindungen transformieren.
- Aktivierungs-/Update-Regeln als Spike-nahe Approximationen modellieren.
- Routing- und Synapsen-Konfiguration statt klassischem Maschinencode erzeugen.
- Genauigkeits- und Energie-Modell als Backend-Capability erfassen.

Meilenstein:

- Ein kleiner klassifizierender Netzwerkblock kann in eine neuromorphe Konfiguration uebersetzt und im Simulator validiert werden.

### 7. Noise-Aware Auto-Tuner

Ziel: TUC optimiert nicht nur Laufzeit, sondern physikalische Robustheit.

Aufgaben:

- Error-Budget-Modell fuer HAC-IR definieren.
- Rauschmodelle pro Backend erfassen: thermisch, Quantisierung, ADC/DAC, sparsity-induced error.
- Tuning-Ziele definieren: Latenz, Energie, Genauigkeit, Robustheit.
- Multi-Objective-Suche implementieren.
- Ergebnisberichte erzeugen: gewaehlte Strategie, verworfene Alternativen, erwarteter Fehler.

Meilenstein:

- Fuer einen photonischen MatMul- oder MLP-Block waehlt der Tuner eine robustere Strategie als die schnellste naive Strategie und belegt das durch Simulation.

### 8. Runtime Und Dynamic Graph Partitioning

Ziel: TUC entscheidet zur Laufzeit, welche Hardware welchen Graphteil ausfuehrt.

Aufgaben:

- Device Discovery bauen: vorhandene GPUs, Spezialgeraete, Simulatoren.
- Unified Execution Plan definieren: Ops, Datenbewegung, Synchronisation, Kalibrierung.
- Cost Model integrieren: Transferkosten, Latenz, Durchsatz, Fehlerbudget.
- Puffer- und Speicherstrategie fuer heterogene Ausfuehrung definieren.
- PyTorch-Integration als optionaler Backend-/Compilerpfad vorbereiten.

Meilenstein:

- Ein Mini-Graph wird automatisch in GPU- und Spezialbackend-Abschnitte geteilt und korrekt ausgefuehrt.

## Zeitplan

### Phase 0: Projektfundament, Monat 0 bis 1

Ergebnis: Das Projekt ist arbeitsfaehig und technisch fokussiert.

Lieferobjekte:

- Architekturentscheidung: Fork, Extension oder Layer ueber Triton.
- Repository-Struktur.
- Build- und Testumgebung.
- Kompatibilitaetsmatrix fuer Triton-Kernels.
- Erste Governance: Maintainer-Modell, RFC-Prozess, Contribution Guidelines.
- Definition der MVP-Kernels.

Go/No-Go:

- Build laeuft lokal und in CI.
- Mindestens ein bestehender Triton-Kernel ist reproduzierbar testbar.

### Phase 1: Triton-Kompatibilitaet Und IR-Skeleton, Monat 1 bis 3

Ergebnis: TUC kann existierende Kernels durch eine kontrollierte Pipeline fuehren.

Lieferobjekte:

- Frontend-Hints als Metadaten.
- TLIR/HAC-IR/HS-IR Skeleton.
- IR-Dumps und Debug-Ausgaben.
- MatMul- und Elementwise-Vertical-Slice.
- Baseline-Benchmarks gegen Triton.

Go/No-Go:

- MatMul laeuft end-to-end.
- Hints gehen durch die Pipeline.
- Keine groben Performance- oder Korrektheitsregressionen im MVP-Scope.

### Phase 2: HAC-IR Und Backend API, Monat 3 bis 6

Ergebnis: TUC wird zu einer echten Plattform statt nur einem Fork.

Lieferobjekte:

- HAC-IR v0.1.
- Backend Capability Schema.
- Plugin-Registrierung.
- Referenz-Simulatorbackend.
- API-Dokumentation fuer Backend-Autoren.

Go/No-Go:

- Ein Toy-Backend kann eine lineare Operation uebernehmen.
- GPU-Backend bleibt fuer MVP-Kernels kompatibel.
- API ist stabil genug fuer externe Experimente.

### Phase 3: Noise-Aware Tuning Und Photonik-Simulator, Monat 6 bis 9

Ergebnis: Der physikalische Compiler-Ansatz wird sichtbar.

Lieferobjekte:

- Photonik-Simulator oder Integrationsschicht.
- Rauschmodell v0.1.
- Tuning-Ziele fuer Geschwindigkeit, Energie und Robustheit.
- Graph-Splitting fuer lineare und nicht-lineare Abschnitte.
- Ergebnisreport fuer Tuning-Entscheidungen.

Go/No-Go:

- TUC kann eine lineare Operation an den Photonik-Simulator delegieren.
- Nicht-lineare Operationen bleiben korrekt auf digitaler Hardware.
- Robustheitsgewinn ist messbar.

### Phase 4: Runtime Partitioning, Monat 9 bis 12

Ergebnis: TUC kann heterogen ausfuehren, nicht nur heterogen kompilieren.

Lieferobjekte:

- Device Discovery.
- Execution Plan Format.
- Datenbewegungs- und Pufferstrategie.
- Mini-PyTorch-Integration oder TorchDynamo-nahe Demo.
- End-to-End-Demo: GPU plus Spezialbackend-Simulator.

Go/No-Go:

- Ein kleiner MLP- oder Attention-Block wird korrekt partitioniert.
- Laufzeitplan ist inspizierbar.
- Die Demo ist reproduzierbar und dokumentiert.

### Phase 5: Jahr 2, Partner-Backends Und Oekosystem

Ergebnis: TUC wird fuer Hardware-Partner relevant.

Lieferobjekte:

- Backend API v1.0.
- Mindestens ein Partner- oder Community-Backend.
- Photonik-Referenzbackend stabilisiert.
- Neuromorpher Simulator/Backend-Prototyp.
- Benchmark- und Model-Zoo fuer heterogene Ausfuehrung.
- RFC-Prozess fuer neue Hardwareklassen.

Go/No-Go:

- Ein kleines externes Team kann ein Backend ohne Kernteam-Unterstuetzung anbinden.
- TUC zeigt fuer mindestens eine Spezialhardwareklasse einen Vorteil bei Energie, Latenz oder Robustheit.

### Phase 6: Jahr 3, PyTorch-Integration Und Standardisierung

Ergebnis: TUC wird ein ernstzunehmender Standardpfad fuer heterogenes KI-Computing.

Lieferobjekte:

- Offizielle oder community-getragene PyTorch-Integration.
- Stabiler Runtime Manager.
- Produktionsnahe Benchmarks.
- Erweiterte Auto-Tuning-Strategien.
- Dokumentierte Backend-Zertifizierung.
- Community-Governance mit mehreren Maintainer-Gruppen.

Go/No-Go:

- TUC kann reale Modelle teilweise partitionieren.
- Mindestens zwei Hardwareklassen werden glaubwuerdig unterstuetzt.
- Backends koennen unabhaengig versioniert und getestet werden.

## Erste 30 Tage

Prioritaet: Den Traum in einen baubaren Kern verwandeln.

Aufgaben:

1. Triton-Codebasis und MLIR-Pipeline analysieren.
2. MVP-Kernels festlegen.
3. Architektur-RFC schreiben: IR-Ebenen, Backend-API, Runtime-Grenzen.
4. Build- und CI-Grundgeruest aufsetzen.
5. Erste Tests fuer MatMul und Elementwise-Kernels erstellen.
6. Frontend-Hints als reine Metadaten einbauen.
7. IR-Dump-Format definieren.

Erfolgskriterium:

- Ein Entwickler kann TUC lokal bauen, einen minimalen Kernel ausfuehren und die erste IR-Zwischenform sehen.

## Erste 60 Tage

Prioritaet: Der erste Vertical Slice.

Aufgaben:

1. TLIR zu HAC-IR fuer MatMul implementieren.
2. HAC-IR zu GPU-HS-IR fuer den gleichen Kernel implementieren.
3. Korrektheitstests gegen Triton-Baseline.
4. Benchmark-Harness aufbauen.
5. Backend-Capability-Modell v0.1 skizzieren.
6. Toy-Backend definieren, das lineare Operationen annimmt.

Erfolgskriterium:

- MatMul laeuft durch die neue Pipeline und erreicht eine akzeptable Baseline-Performance.

## Erste 90 Tage

Prioritaet: Plattformbeweis.

Aufgaben:

1. Elementwise und Reduction in HAC-IR aufnehmen.
2. Backend-Plugin-Registrierung implementieren.
3. Simuliertes Spezialbackend anbinden.
4. Einfache Partitionierung zwischen GPU und Toy-Backend bauen.
5. Erste Dokumentation fuer Backend-Autoren schreiben.
6. Roadmap fuer Photonik-Simulator finalisieren.

Erfolgskriterium:

- TUC kann einen kleinen Graphen analysieren, einen Teil an ein Spezialbackend delegieren und den Rest auf GPU ausfuehren.

## Erfolgsmessung

Technische Metriken:

- Kernel-Korrektheit gegen Triton-Baselines.
- Performance relativ zu Triton/cuBLAS/rocBLAS.
- Anzahl unterstuetzter HAC-IR-Ops.
- Zeit, die ein externer Entwickler fuer ein Toy-Backend braucht.
- Genauigkeitsverlust unter simuliertem Rauschen.
- Datenbewegungskosten bei heterogener Partitionierung.

Oekosystem-Metriken:

- Anzahl externer Contributors.
- Anzahl Backend-Prototypen.
- Dokumentationsqualitaet gemessen an erfolgreichen Onboarding-Versuchen.
- Wiederholbare Demos und Benchmarks.

## Hauptrisiken

### Risiko: Die IR Wird Zu Allgemein

Wenn HAC-IR versucht, jede Hardware abstrakt zu beschreiben, wird sie unbrauchbar.

Gegenmassnahme:

- HAC-IR zuerst aus konkreten Kernels ableiten.
- Nur Ops aufnehmen, die im MVP wirklich gebraucht werden.
- Erweiterungen ueber RFCs steuern.

### Risiko: GPU-Kompatibilitaet Leidet

Wenn bestehende Triton-Nutzer Performance verlieren, entsteht kein Vertrauen.

Gegenmassnahme:

- GPU-Baseline als harte CI-Metrik.
- Neue IR-Pfade zuerst optional machen.
- Performance-Regressions sichtbar und blockierend machen.

### Risiko: Exotische Hardware Ist Nicht Verfuegbar

Ohne reale Chips koennte TUC abstrakt bleiben.

Gegenmassnahme:

- Simulator-first-Strategie.
- Capability- und Noise-Modelle als Backend-Vertrag.
- Fruehe Partnergespraeche, aber keine Roadmap-Abhaengigkeit von einem einzelnen Partner.

### Risiko: Runtime-Partitionierung Wird Zu Komplex

Automatische Graph-Aufteilung kann schnell explodieren.

Gegenmassnahme:

- Erst regelbasierte Partitionierung.
- Kostenmodelle klein halten.
- Entscheidungen erklaerbar machen.
- Manuelle Overrides erlauben.

### Risiko: Open-Source-Governance Ist Zu Spaet

Ein Universal-Compiler braucht Vertrauen von Hardware-Partnern und Entwicklern.

Gegenmassnahme:

- RFC-Prozess frueh einrichten.
- Backend-API offen dokumentieren.
- Kompatibilitaets- und Zertifizierungstests bereitstellen.

## Teamstruktur Fuer Den Start

Minimalteam:

- Compiler Lead: Architektur, MLIR, Pass-Pipeline.
- Triton Engineer: Kompatibilitaet, GPU-Backends, Benchmarks.
- Runtime Engineer: Device Discovery, Execution Plan, PyTorch-Integration.
- Backend/API Engineer: Plugin-System, Capability-Modell.
- Research Engineer: Noise-Modelle, Photonik-/Neuromorphik-Simulatoren.
- Developer Experience Engineer: Dokumentation, Debuggability, Onboarding.

## Kernentscheidung

TUC sollte in der ersten Phase nicht versuchen, "Universal" vollstaendig einzuloesen. Es sollte beweisen, dass Universalitaet als Architektur moeglich ist.

Der richtige erste Claim lautet:

"Wir koennen bestehende Triton-Kernels kompatibel halten, eine hardwareagnostische Compute-IR einfuehren und einen Teil der Arbeit ueber eine dokumentierte Backend-API an Spezialhardware oder Simulatoren delegieren."

Wenn dieser Claim belastbar ist, wird aus der Vision eine Plattform.
