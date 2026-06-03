import pandas as pd

from src.active_program_sources import build_program_sources, program_id_from_code


def test_program_id_from_code_normalizes_local_code():
    assert program_id_from_code("BA.ECON:ECG") == "ba_econ_ecg"


def test_build_program_sources_marks_shared_cips_and_review_notes():
    clean = pd.DataFrame(
        {
            "master_program_code": ["BA.CLEG", "BA.CMLC", "BS.COMP"],
            "program_name_source": [
                "Interdisciplinary St: Comm, Legal Inst, Econ, Gov (BA)",
                "Communication, Language, and Culture (BA)",
                "Computer Science (BS)",
            ],
            "cip": ["30.9999", "30.9999", "11.0701"],
            "school_college": ["SPA", "SOC", "CAS"],
            "program_status": ["A", "A", "A"],
            "needs_review": ["False", "True", "False"],
            "review_note": ["", "No exact master row; verify display name.", ""],
        }
    )

    inventory, cip_map = build_program_sources(clean)

    assert list(inventory["program_id"]) == ["ba_cleg", "ba_cmlc", "bs_comp"]
    assert inventory.loc[1, "program_name_verified"] == "TRUE"
    assert "Cleanup review flag" in inventory.loc[1, "program_notes"]

    shared = cip_map[cip_map["cip"] == "30.9999"]
    assert set(shared["cip_mapping_type"]) == {"multiple_programs_share_cip"}
    assert shared["cip_mapping_verified"].eq("TRUE").all()
    single = cip_map[cip_map["program_id"] == "bs_comp"].iloc[0]
    assert single["cip_mapping_type"] == "one_program_to_one_cip"
