"""Collector implementations. Each module registers one or more Collector
subclasses via the @source decorator; datalake.collector.load_sources()
imports them all so they land in the REGISTRY."""
