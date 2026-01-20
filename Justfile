# Justfile for RAR project

# Run the main script
run *args:
    python src/gvsu_snow_removal_scheduler/main.py {{args}}

# Run tests
test:
    pytest
