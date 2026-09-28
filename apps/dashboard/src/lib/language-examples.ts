export const languageExamples = [
  {
    name: "System & Identity Baseline",
    source: `case "Baseline triage" {
  hunt "system-identity-baseline" {
    targets { group "AUTHORIZED" os windows | linux }
    runtime {
      backend llvm
      execution memory
      variant { enabled true seed auto profile minimal }
    }
    capabilities {
      system.read
      users.read
      process.read
      network.read
    }
    budget { cpu <= 15% memory <= 192MB io <= 100MB duration <= 90s }

    collect system as system_info
    collect users as accounts
    collect interfaces as interfaces

    collect processes as process_inventory
    collect connections as connection_inventory
  }
}`,
  },
  {
    name: "Process & Network Triage",
    source: `case "Process network triage" {
  hunt "process-network-triage" {
    targets { group "AUTHORIZED" os windows | linux }
    runtime {
      backend llvm
      execution memory
      variant { enabled true seed 0x2a profile balanced }
    }
    capabilities {
      process.read
      network.read
    }
    budget { cpu <= 18% memory <= 224MB io <= 125MB duration <= 105s }

    collect processes as processes
    collect connections as connections
    collect routes as routes
  }
}`,
  },
  {
    name: "Network Surface Snapshot",
    source: `case "Network surface inventory" {
  hunt "network-surface-snapshot" {
    targets { group "AUTHORIZED" os windows | linux }
    runtime {
      backend llvm
      execution memory
      variant { enabled true seed 0x73 profile minimal }
    }
    capabilities {
      process.read
      network.read
    }
    budget { cpu <= 12% memory <= 160MB io <= 80MB duration <= 75s }

    collect interfaces as interface_inventory
    collect routes as route_inventory
    collect connections as connection_inventory

    collect processes as process_inventory
  }
}`,
  },
  {
    name: "Driver & System Inventory",
    source: `case "Driver inventory" {
  hunt "driver-system-inventory" {
    targets { group "AUTHORIZED" os windows | linux }
    runtime {
      backend llvm
      execution memory
      variant { enabled true seed 0x91 profile balanced }
    }
    capabilities {
      system.read
      drivers.read
      process.read
      network.read
    }
    budget { cpu <= 16% memory <= 208MB io <= 110MB duration <= 100s }

    collect system as host_system
    collect drivers as driver_inventory

    collect processes as process_inventory
    collect connections as connection_inventory
  }
}`,
  },
  {
    name: "Comprehensive Endpoint Sweep",
    source: `case "Comprehensive endpoint sweep" {
  hunt "comprehensive-endpoint-sweep" {
    targets { group "AUTHORIZED" os windows | linux }
    runtime {
      backend llvm
      execution memory
      variant { enabled true seed auto profile balanced }
    }
    capabilities {
      system.read
      users.read
      process.read
      network.read
      drivers.read
    }
    budget { cpu <= 20% memory <= 256MB io <= 150MB duration <= 120s }

    collect system as system_info
    collect users as accounts
    collect processes as process_inventory
    collect interfaces as interface_inventory
    collect connections as connection_inventory
    collect routes as route_inventory
    collect drivers as driver_inventory
  }
}`,
  },
];
