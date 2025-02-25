# ZMap Network Scanner Makefile

.PHONY: all test build run clean docker

all: test build

# Run tests
test:
	cd Scripts && python -m pytest test_zmap_scanner.py -v

# Run static type checking
lint:
	pylint Scripts/*.py

# Build Docker image
docker-build:
	docker build -t zmap-scanner -f docker_scanner_build .

# Run scanner with Docker
docker-run:
	docker run -v $(PWD)/Data:/app/data -v $(PWD)/output:/app/output zmap-scanner

# Run scanner locally
run:
	python Scripts/zmap_postal_code_availability.py --input Data/input.csv

# Run visualization locally
visualize:
	python Scripts/zmap_visualizing_response_rate.py

# Clean output files
clean:
	rm -f networks_and_ips.csv networks.txt
	rm -f output/*.png

# Help
help:
	@echo "ZMap Network Scanner Makefile"
	@echo ""
	@echo "Available targets:"
	@echo "  all          - Run tests and build Docker image"
	@echo "  test         - Run tests"
	@echo "  lint         - Run pylint on Python files"
	@echo "  docker-build - Build Docker image"
	@echo "  docker-run   - Run scanner in Docker container"
	@echo "  run          - Run scanner locally"
	@echo "  visualize    - Run visualization locally"
	@echo "  clean        - Clean output files"