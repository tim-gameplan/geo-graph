.PHONY: up build-water build-grid topology
up:
	docker compose up -d
build-water:
	psql -f sql/build_water_buffers.sql -v buf_m=50
build-grid:
	psql -f sql/build_terrain_grid.sql -v profile=default
topology:
	psql -f sql/refresh_topology.sql
