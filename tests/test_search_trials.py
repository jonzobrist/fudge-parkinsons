"""Offline unit tests for the trial-search helper. No network required."""

import argparse
import importlib.util
import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SCRIPT = (
    Path(__file__).resolve().parent.parent
    / "skills"
    / "fuck-parkinsons"
    / "scripts"
    / "search_trials.py"
)
spec = importlib.util.spec_from_file_location("search_trials", SCRIPT)
search_trials = importlib.util.module_from_spec(spec)
sys.modules["search_trials"] = search_trials
spec.loader.exec_module(search_trials)


def make_args(**overrides):
    defaults = {
        "condition": "Parkinson disease",
        "terms": "",
        "country": "United States",
        "state": "",
        "city": "",
        "near": None,
        "radius_miles": 50.0,
        "limit": 10,
        "full_criteria": False,
        "output": None,
    }
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


def make_study(nct_id="NCT00000001", overall_status="RECRUITING", locations=None):
    return {
        "protocolSection": {
            "identificationModule": {
                "nctId": nct_id,
                "briefTitle": "A study",
            },
            "statusModule": {
                "overallStatus": overall_status,
                "lastUpdatePostDateStruct": {"date": "2026-01-01"},
            },
            "designModule": {"phases": ["PHASE3"], "studyType": "INTERVENTIONAL"},
            "armsInterventionsModule": {
                "interventions": [{"name": "Investigational study drug", "type": "DRUG"}],
            },
            "eligibilityModule": {
                "minimumAge": "18 Years",
                "maximumAge": "",
                "sex": "ALL",
                "eligibilityCriteria": "Inclusion: adults.",
            },
            "contactsLocationsModule": {
                "locations": locations
                or [
                    {
                        "facility": "General Hospital",
                        "status": "RECRUITING",
                        "city": "Los Angeles",
                        "state": "California",
                        "country": "United States",
                    }
                ],
            },
        }
    }


def make_result(title, phases, intervention_types, eligibility=""):
    return {
        "title": title,
        "overall_status": "RECRUITING",
        "last_updated": "2026-08-01",
        "phases": phases,
        "study_type": "INTERVENTIONAL",
        "interventions": [],
        "intervention_types": intervention_types,
        "eligibility_criteria": eligibility,
    }


class NormalizationTests(unittest.TestCase):
    def test_default_condition_and_limit(self):
        args = search_trials.parse_args(["--country", "USA"])
        self.assertEqual(args.condition, "Parkinson Disease")
        self.assertEqual(args.limit, 5)

    def test_condition_can_be_refined(self):
        args = search_trials.parse_args(
            ["--country", "USA", "--condition", "Multiple System Atrophy"]
        )
        self.assertEqual(args.condition, "Multiple System Atrophy")

    def test_parkinson_name_variants_match(self):
        expected = {"parkinson"}
        for value in ("Parkinson Disease", "Parkinson's disease", "Parkinson’s", "Parkinsons"):
            self.assertEqual(search_trials.query_tokens(value), expected)

    def test_country_aliases_expand(self):
        self.assertEqual(search_trials.normalize_country("USA"), "United States")
        self.assertEqual(search_trials.normalize_country("u.s."), "United States")
        self.assertEqual(search_trials.normalize_country("UK"), "United Kingdom")

    def test_unknown_country_passes_through(self):
        self.assertEqual(search_trials.normalize_country("France"), "France")

    def test_state_aliases_expand(self):
        self.assertEqual(search_trials.normalize_state("CA"), "California")
        self.assertEqual(search_trials.normalize_state("on"), "Ontario")

    def test_parse_args_normalizes_location(self):
        args = search_trials.parse_args(
            ["--condition", "Parkinson disease", "--country", "usa", "--state", "ca"]
        )
        self.assertEqual(args.country, "United States")
        self.assertEqual(args.state, "California")


class SiteMatchesTests(unittest.TestCase):
    def test_open_site_matches(self):
        location = {"status": "RECRUITING", "country": "United States"}
        self.assertTrue(
            search_trials.site_matches(location, make_args(), "RECRUITING")
        )

    def test_closed_site_rejected(self):
        location = {"status": "COMPLETED", "country": "United States"}
        self.assertFalse(
            search_trials.site_matches(location, make_args(), "RECRUITING")
        )

    def test_missing_site_status_falls_back_to_study_status(self):
        location = {"country": "United States"}
        self.assertTrue(
            search_trials.site_matches(location, make_args(), "RECRUITING")
        )
        self.assertFalse(
            search_trials.site_matches(location, make_args(), "COMPLETED")
        )

    def test_location_filters_are_case_insensitive(self):
        location = {
            "status": "RECRUITING",
            "city": "los angeles",
            "state": "california",
            "country": "united states",
        }
        args = make_args(state="California", city="Los Angeles")
        self.assertTrue(search_trials.site_matches(location, args, "RECRUITING"))

    def test_wrong_state_rejected(self):
        location = {
            "status": "RECRUITING",
            "state": "Texas",
            "country": "United States",
        }
        args = make_args(state="California")
        self.assertFalse(search_trials.site_matches(location, args, "RECRUITING"))


class ExtractTests(unittest.TestCase):
    def test_closed_study_is_rejected_even_with_recruiting_site(self):
        self.assertIsNone(search_trials.extract(make_study(overall_status="COMPLETED"), make_args()))

    def test_site_access_is_explicit(self):
        for status in search_trials.OPEN_STATUSES:
            study = make_study(locations=[{
                "facility": "Study site", "status": status, "country": "United States"
            }])
            result = search_trials.extract(study, make_args())
            self.assertEqual(result["candidate_sites"][0]["recruitment_access"], status)

    def test_closed_nearby_site_not_reported_as_open(self):
        study = make_study(locations=[
            {"facility": "Closed", "status": "COMPLETED", "country": "United States"},
            {"facility": "Open", "status": "RECRUITING", "country": "United States"},
        ])
        result = search_trials.extract(study, make_args())
        self.assertEqual([site["facility"] for site in result["candidate_sites"]], ["Open"])

    def test_extracts_matching_study(self):
        result = search_trials.extract(make_study(), make_args())
        self.assertIsNotNone(result)
        self.assertEqual(result["nct_id"], "NCT00000001")
        self.assertEqual(result["candidate_sites"][0]["status"], "RECRUITING")

    def test_returns_none_without_matching_site(self):
        study = make_study(
            locations=[
                {
                    "facility": "Foreign Site",
                    "status": "RECRUITING",
                    "city": "Paris",
                    "state": "",
                    "country": "France",
                }
            ]
        )
        self.assertIsNone(search_trials.extract(study, make_args()))

    def test_missing_site_status_is_labeled_not_dropped(self):
        study = make_study(
            locations=[
                {
                    "facility": "General Hospital",
                    "city": "Los Angeles",
                    "state": "California",
                    "country": "United States",
                }
            ]
        )
        result = search_trials.extract(study, make_args())
        self.assertIsNotNone(result)
        self.assertEqual(
            result["candidate_sites"][0]["status"], "not listed (study is RECRUITING)"
        )
        self.assertEqual(result["candidate_sites"][0]["recruitment_access"], "UNVERIFIED")

    def test_observational_study_without_phases_is_retained(self):
        study = make_study()
        study["protocolSection"]["designModule"] = {"studyType": "OBSERVATIONAL"}
        result = search_trials.extract(study, make_args())
        self.assertEqual(result["study_type"], "OBSERVATIONAL")
        self.assertEqual(result["phases"], [])

    def test_long_criteria_truncated_by_default(self):
        study = make_study()
        study["protocolSection"]["eligibilityModule"]["eligibilityCriteria"] = (
            "x" * 5000
        )
        result = search_trials.extract(study, make_args())
        self.assertIn("[Truncated", result["eligibility_criteria"])
        self.assertLess(len(result["eligibility_criteria"]), 2200)

    def test_full_criteria_flag_keeps_everything(self):
        study = make_study()
        study["protocolSection"]["eligibilityModule"]["eligibilityCriteria"] = (
            "x" * 5000
        )
        result = search_trials.extract(study, make_args(full_criteria=True))
        self.assertEqual(len(result["eligibility_criteria"]), 5000)


class SortingTests(unittest.TestCase):
    def test_prioritizes_requested_rehabilitation_over_unrelated_drug(self):
        args = make_args(condition="Parkinson Disease", terms="freezing gait exercise")
        drug = make_result("Parkinson disease drug study", ["PHASE3"], ["DRUG"])
        exercise = make_result(
            "Exercise for freezing of gait in Parkinson disease", [], ["BEHAVIORAL"]
        )
        ranked = search_trials.rank_results([drug, exercise], args)
        self.assertIs(ranked[0], exercise)

    def test_no_automatic_drug_phase_or_study_type_preference(self):
        args = make_args()
        observational = make_result("Parkinson disease study", [], [])
        observational["study_type"] = "OBSERVATIONAL"
        behavioral = make_result("Parkinson disease study", ["NA"], ["BEHAVIORAL"])
        drug = make_result("Parkinson disease study", ["PHASE3"], ["DRUG"])
        ranked = search_trials.rank_results([observational, behavioral, drug], args)
        self.assertEqual(ranked, [observational, behavioral, drug])
        self.assertEqual(search_trials.relevance_score(observational, args),
                         search_trials.relevance_score(drug, args))

    def test_prioritizes_user_terms(self):
        args = make_args(terms="LRRK2")
        generic = make_result("Parkinson disease study", ["PHASE3"], ["DRUG"])
        matching = make_result("LRRK2 Parkinson disease study", ["PHASE1"], ["DRUG"])
        ranked = search_trials.rank_results([generic, matching], args)
        self.assertIs(ranked[0], matching)

    def test_api_order_breaks_exact_ties(self):
        args = make_args()
        first = make_result("Zebra", ["PHASE2"], ["DRUG"])
        second = make_result("Apple", ["PHASE2"], ["DRUG"])

        ranked = search_trials.rank_results([first, second], args)

        self.assertEqual([item["title"] for item in ranked], ["Zebra", "Apple"])


class FetchTests(unittest.TestCase):
    def test_retrieval_cap_is_reported(self):
        with mock.patch.object(search_trials, "MAX_PAGES", 2), mock.patch.object(
            search_trials, "get_json", return_value={"studies": [{"id": 1}], "nextPageToken": "more"}
        ):
            studies, truncated = search_trials.fetch_studies(make_args())
        self.assertTrue(truncated)
        self.assertEqual(len(studies), 2)

    def test_uses_normalized_location_and_paginates(self):
        args = search_trials.parse_args(
            ["--condition", "Parkinson disease", "--country", "USA", "--state", "CA"]
        )
        responses = [
            {"studies": [{"id": 1}], "nextPageToken": "next"},
            {"studies": [{"id": 2}]},
        ]

        with mock.patch.object(search_trials, "get_json", side_effect=responses) as get_json:
            studies, truncated = search_trials.fetch_studies(args)

        self.assertEqual(studies, [{"id": 1}, {"id": 2}])
        self.assertFalse(truncated)
        first_url = get_json.call_args_list[0].args[0]
        second_url = get_json.call_args_list[1].args[0]
        self.assertIn("query.locn=California%2C+United+States", first_url)
        self.assertIn("pageToken=next", second_url)


LOS_ANGELES = (34.0522, -118.2437)


class GeoTests(unittest.TestCase):
    def test_parse_near_accepts_lat_lon(self):
        self.assertEqual(search_trials.parse_near("34.05, -118.24"), (34.05, -118.24))
        self.assertIsNone(search_trials.parse_near(""))

    def test_parse_near_rejects_bad_input(self):
        for value in ("Los Angeles", "34.05", "95,0", "a,b", "nan,0", "0,inf"):
            with self.assertRaises(argparse.ArgumentTypeError):
                search_trials.parse_near(value)

    def test_distance_is_roughly_correct(self):
        # Los Angeles to San Diego is about 112 miles.
        miles = search_trials.distance_miles(LOS_ANGELES, {"lat": 32.7157, "lon": -117.1611})
        self.assertAlmostEqual(miles, 112, delta=5)
        self.assertIsNone(search_trials.distance_miles(LOS_ANGELES, {}))

    def test_invalid_site_coordinates_are_excluded(self):
        for point in ({"lat": float("nan"), "lon": 0}, {"lat": 0, "lon": 190}):
            self.assertIsNone(search_trials.distance_miles(LOS_ANGELES, point))

    def test_near_keeps_close_sites_and_drops_far_or_unlocated_ones(self):
        args = make_args(near=LOS_ANGELES, radius_miles=40)
        close = {"status": "RECRUITING", "country": "United States",
                 "city": "Torrance", "geoPoint": {"lat": 33.8358, "lon": -118.3406}}
        far = {"status": "RECRUITING", "country": "United States",
               "city": "San Diego", "geoPoint": {"lat": 32.7157, "lon": -117.1611}}
        unlocated = {"status": "RECRUITING", "country": "United States", "city": "Unknown"}
        self.assertTrue(search_trials.site_matches(close, args, "RECRUITING"))
        self.assertFalse(search_trials.site_matches(far, args, "RECRUITING"))
        self.assertFalse(search_trials.site_matches(unlocated, args, "RECRUITING"))

    def test_extract_reports_distance_and_sorts_nearest_first(self):
        args = make_args(near=LOS_ANGELES, radius_miles=60)
        study = make_study(locations=[
            {"facility": "Far", "status": "RECRUITING", "city": "Irvine",
             "country": "United States", "geoPoint": {"lat": 33.6695, "lon": -117.8231}},
            {"facility": "Near", "status": "RECRUITING", "city": "Beverly Hills",
             "country": "United States", "geoPoint": {"lat": 34.0736, "lon": -118.4004}},
        ])
        result = search_trials.extract(study, args)
        self.assertEqual([site["facility"] for site in result["candidate_sites"]], ["Near", "Far"])
        self.assertLess(result["candidate_sites"][0]["distance_miles"], 15)

    def test_fetch_sends_geo_filter(self):
        args = search_trials.parse_args([
            "--condition", "Parkinson disease", "--country", "USA",
            "--near", "34.05,-118.24", "--radius-miles", "40",
        ])
        with mock.patch.object(search_trials, "get_json", return_value={"studies": []}) as get_json:
            search_trials.fetch_studies(args)
        self.assertIn("filter.geo=distance%2834.05%2C-118.24%2C40.0mi%29", get_json.call_args.args[0])


class MainTests(unittest.TestCase):
    def run_main(self, args, responses):
        stdout, stderr = io.StringIO(), io.StringIO()
        with mock.patch.object(sys, "argv", ["search_trials.py"] + args), \
                mock.patch.object(search_trials, "get_json", side_effect=responses), \
                contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = search_trials.main()
        return code, stdout.getvalue(), stderr.getvalue()

    def test_successful_payload_warns_about_access_and_preserves_metadata(self):
        code, output, error = self.run_main(
            ["--country", "USA"],
            [{"studies": [make_study()]}, {"dataTimestamp": "2026-11-01"}],
        )
        self.assertEqual(code, 0)
        self.assertEqual(error, "")
        payload = json.loads(output)
        self.assertEqual(payload["search"]["condition"], "Parkinson Disease")
        self.assertEqual(payload["clinicaltrials_gov_data_timestamp"], "2026-11-01")
        self.assertIn("unverified", payload["warning"])
        self.assertEqual(payload["results"][0]["candidate_sites"][0]["recruitment_access"], "RECRUITING")

    def test_request_failure_exits_nonzero(self):
        code, output, error = self.run_main(["--country", "USA"], [OSError("offline")])
        self.assertEqual(code, 1)
        self.assertEqual(output, "")
        self.assertIn("request failed", error)

    def test_invalid_radius_or_limit_exits_before_network(self):
        for args in (["--radius-miles", "nan"], ["--radius-miles", "inf"],
                     ["--radius-miles", "0"], ["--limit", "0"]):
            code, output, _ = self.run_main(["--country", "USA"] + args, [])
            self.assertEqual(code, 2)
            self.assertEqual(output, "")

    def test_writes_json_to_requested_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "nested" / "candidates.json"
            code, output, error = self.run_main(
                ["--country", "USA", "--output", str(path)],
                [{"studies": []}, {"dataTimestamp": "2026-11-01"}],
            )
            self.assertEqual(code, 0)
            self.assertEqual(error, "")
            self.assertIn("Wrote 0", output)
            self.assertEqual(json.loads(path.read_text())["results"], [])


if __name__ == "__main__":
    unittest.main()
