from src import config


def test_core_constants():
    assert config.AU_UNITID == 131159
    assert config.DC_MSA_CODE == "47900"
    assert config.BACHELORS_AWLEVEL == 5
    assert config.FIRST_MAJOR == 1


def test_paths_are_under_project_root():
    for p in (config.RAW_DIR, config.PROCESSED_DIR, config.OUTPUT_DIR, config.LOG_DIR):
        assert str(p).startswith(str(config.PROJECT_ROOT))


def test_catch_all_and_education_sets():
    assert "11-1021" in config.CATCH_ALL_SOCS  # General and Operations Managers
    assert "Bachelor's degree" in config.BACHELORS_PLUS_EDUCATION
    assert "Associate's degree" not in config.BACHELORS_PLUS_EDUCATION
