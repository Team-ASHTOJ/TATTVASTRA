export const languageExamples = [
  { name: "System Baseline", capability: "system.read", collector: "system" },
  {
    name: "Process Investigation",
    capability: "process.read",
    collector: "processes",
  },
  {
    name: "Network Investigation",
    capability: "network.read",
    collector: "connections",
  },
  {
    name: "Driver Inventory",
    capability: "drivers.read",
    collector: "drivers",
  },
].map((item) => ({
  name: item.name,
  source: `hunt "${item.name.toLowerCase().replaceAll(" ", "-")}" {\n    targets { group "AUTHORIZED" os windows | linux }\n    runtime { backend llvm execution memory }\n    capabilities { ${item.capability} }\n    collect ${item.collector} as inventory\n}`,
}));
languageExamples.push({
  name: "Combined Investigation",
  source: `hunt "combined-investigation" {
    targets { group "AUTHORIZED" os windows | linux }
    runtime { backend llvm execution memory }
    capabilities { system.read process.read network.read drivers.read }
    collect system as sys
    collect processes as procs
    collect connections as conns
    collect drivers as drv
}`,
});
