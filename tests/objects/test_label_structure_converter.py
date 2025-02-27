"""
All tests regarding converting from and to Encord dict to the label row.
"""
import pytest
from dataclasses import asdict
from typing import Any, Dict, List, Union
from unittest.mock import Mock, PropertyMock

from deepdiff import DeepDiff

from encord.objects.ontology_labels_impl import LabelRowV2, OntologyStructure
from encord.orm.label_row import LabelRowMetadata
from tests.objects.common import FAKE_LABEL_ROW_METADATA
from tests.objects.data import (
    data_1,
    empty_video,
    image_group_with_reviews,
    native_image_data,
    video_with_dynamic_classifications,
)
from tests.objects.data.all_ontology_types import all_ontology_types
from tests.objects.data.dicom_labels import dicom_labels

from tests.objects.data.ontology_with_many_dynamic_classifications import ontology as ontology_with_many_dynamic_classifications
from tests.objects.data.dynamic_classifications_ontology import (
    dynamic_classifications_ontology,
)
from tests.objects.data.empty_image_group import (
    empty_image_group_labels,
    empty_image_group_ontology,
)
from tests.objects.data.image_group import image_group_labels, image_group_ontology


def ontology_from_dict(ontology_structure_dict: Dict):
    ontology = Mock()
    ontology.structure = OntologyStructure.from_dict(ontology_structure_dict)
    return ontology


def deep_diff_enhanced(actual: Union[dict, list], expected: Union[dict, list], exclude_regex_paths: List[str] = None):
    """Basically a deep diff but with an normal assert after. `DeepDiff` to be able to exclude
    regex paths, and `assert` to see an easily comparable diff with tools such as Pycharm."""
    if exclude_regex_paths is None:
        exclude_regex_paths = []
    if DeepDiff(
        expected,
        actual,
        ignore_order=True,
        exclude_regex_paths=exclude_regex_paths,
    ):
        print(DeepDiff(expected, actual, ignore_order=True, exclude_regex_paths=exclude_regex_paths))
        assert expected == actual


def test_serialise_image_group_with_classifications():
    label_row_metadata_dict = asdict(FAKE_LABEL_ROW_METADATA)
    label_row_metadata_dict["duration"] = None
    label_row_metadata_dict["frames_per_second"] = None
    label_row_metadata_dict["number_of_frames"] = 5
    label_row_metadata = LabelRowMetadata(**label_row_metadata_dict)

    label_row = LabelRowV2(label_row_metadata, Mock(), ontology_from_dict(empty_image_group_ontology))
    label_row.from_labels_dict(empty_image_group_labels)

    actual = label_row.to_encord_dict()
    assert empty_image_group_labels == actual

    label_row = LabelRowV2(label_row_metadata, Mock(), ontology_from_dict(image_group_ontology))
    label_row.from_labels_dict(image_group_labels)

    actual = label_row.to_encord_dict()
    deep_diff_enhanced(
        image_group_labels,
        actual,
        exclude_regex_paths=["\['reviews'\]", "\['isDeleted'\]", "\['createdAt'\]", "\['lastEditedAt'\]"],
    )
    # TODO: I'm only not comparing dates because of timezone differences. This should be done properly.
    #  Probably I can just save timezone information to ensure that going back will not crash the timezone.


def test_serialise_video():
    label_row_metadata_dict = asdict(FAKE_LABEL_ROW_METADATA)
    label_row_metadata_dict["duration"] = 153.16
    label_row_metadata_dict["frames_per_second"] = 25.0
    label_row_metadata = LabelRowMetadata(**label_row_metadata_dict)

    label_row = LabelRowV2(label_row_metadata, Mock(), ontology_from_dict(data_1.ontology))
    label_row.from_labels_dict(data_1.labels)

    # TODO: also check at this point whether the internal data is correct.

    actual = label_row.to_encord_dict()
    deep_diff_enhanced(
        actual,
        data_1.labels,
        exclude_regex_paths=["\['reviews'\]", "\['isDeleted'\]", "\['createdAt'\]", "\['lastEditedAt'\]"],
    )


def test_serialise_image_with_object_answers():
    label_row_metadata_dict = asdict(FAKE_LABEL_ROW_METADATA)
    label_row_metadata_dict["duration"] = None
    label_row_metadata_dict["frames_per_second"] = None
    label_row_metadata_dict["number_of_frames"] = 1
    label_row_metadata = LabelRowMetadata(**label_row_metadata_dict)

    label_row = LabelRowV2(label_row_metadata, Mock(), ontology_from_dict(all_ontology_types))
    label_row.from_labels_dict(native_image_data.labels)

    actual = label_row.to_encord_dict()

    deep_diff_enhanced(
        actual,
        native_image_data.labels,
        exclude_regex_paths=["\['reviews'\]", "\['isDeleted'\]", "\['createdAt'\]", "\['lastEditedAt'\]"],
    )


def test_serialise_dicom_with_dynamic_classifications():
    label_row_metadata_dict = asdict(FAKE_LABEL_ROW_METADATA)
    label_row_metadata_dict["duration"] = None
    label_row_metadata_dict["frames_per_second"] = None
    label_row_metadata_dict["number_of_frames"] = 5
    label_row_metadata = LabelRowMetadata(**label_row_metadata_dict)

    label_row = LabelRowV2(label_row_metadata, Mock(), ontology_from_dict(dynamic_classifications_ontology))
    assert label_row.number_of_frames == label_row_metadata.number_of_frames
    assert label_row.duration == label_row_metadata.duration
    assert label_row.fps == label_row_metadata.frames_per_second

    label_row.from_labels_dict(dicom_labels)

    assert label_row.number_of_frames == label_row_metadata.number_of_frames
    assert label_row.duration == label_row_metadata.duration
    assert label_row.fps == label_row_metadata.frames_per_second

    assert label_row.data_link is None
    assert label_row.height == 256
    assert label_row.width == 256

    actual = label_row.to_encord_dict()

    deep_diff_enhanced(
        actual,
        dicom_labels,
        # Adding the exclude of createdAt and lastEditedAt to unblock pipeline blocks due to UTC vs GMT string dates.
        # Ideally this will be fixed "properly"
        exclude_regex_paths=["\['trackHash'\]", "\['data_links'\]", "\['createdAt'\]", "\['lastEditedAt'\]"],
    )
    # NOTE: likely we do not care about the trackHash. If we end up caring about it, we'll have to ensure that we can
    #  set it from parsing the data and keep it around when setting new answers for example.


def test_dynamic_classifications():
    label_row_metadata_dict = asdict(FAKE_LABEL_ROW_METADATA)
    label_row_metadata_dict["duration"] = 0.08
    label_row_metadata_dict["frames_per_second"] = 25.0
    label_row_metadata = LabelRowMetadata(**label_row_metadata_dict)

    label_row = LabelRowV2(label_row_metadata, Mock(), ontology_from_dict(ontology_with_many_dynamic_classifications))
    label_row.from_labels_dict(video_with_dynamic_classifications.labels)

    actual = label_row.to_encord_dict()

    deep_diff_enhanced(
        actual,
        video_with_dynamic_classifications.labels,
        # Adding the exclude of createdAt and lastEditedAt to unblock pipeline blocks due to UTC vs GMT string dates.
        # Ideally this will be fixed "properly"
        exclude_regex_paths=["\['trackHash'\]", "\['createdAt'\]", "\['lastEditedAt'\]"],
    )


def test_uninitialised_label_row():
    label_row_metadata_dict = asdict(FAKE_LABEL_ROW_METADATA)
    label_row_metadata_dict["duration"] = 0.08
    label_row_metadata_dict["frames_per_second"] = 25.0
    label_row_metadata_dict["label_hash"] = None
    label_row_metadata_dict["created_at"] = None
    label_row_metadata_dict["last_edited_at"] = None
    label_row_metadata = LabelRowMetadata(**label_row_metadata_dict)

    label_row = LabelRowV2(label_row_metadata, Mock(), ontology_from_dict(all_ontology_types))

    assert label_row.label_hash is None
    assert label_row.created_at is None
    assert label_row.last_edited_at is None
    assert label_row.is_labelling_initialised is False

    label_row.from_labels_dict(empty_video.labels)

    assert label_row.label_hash is not None
    assert label_row.created_at is not None
    assert label_row.last_edited_at is not None
    assert label_row.is_labelling_initialised is True


def _remove_reviews(labels: Dict[str, Any]) -> Dict[str, Any]:
    if "reviews" in labels:
        del labels["reviews"]
    for key, value in labels.items():
        if isinstance(value, dict):
            labels[key] = _remove_reviews(value)
        elif isinstance(value, list):
            for index, item in enumerate(value):
                if isinstance(item, dict):
                    value[index] = _remove_reviews(item)
    return labels


def test_label_row_with_reviews():
    label_row_metadata_dict = asdict(FAKE_LABEL_ROW_METADATA)
    label_row_metadata_dict["duration"] = None
    label_row_metadata_dict["frames_per_second"] = None
    label_row_metadata_dict["number_of_frames"] = 5
    label_row_metadata = LabelRowMetadata(**label_row_metadata_dict)

    label_row = LabelRowV2(label_row_metadata, Mock(), ontology_from_dict(all_ontology_types))
    label_row.from_labels_dict(image_group_with_reviews.labels)

    first_object = label_row.get_object_instances()[0]
    first_frame = first_object.get_annotations()[0]

    assert isinstance(first_frame.reviews, list)

    actual = label_row.to_encord_dict()

    expected_no_reviews = _remove_reviews(image_group_with_reviews.labels)
    deep_diff_enhanced(
        expected_no_reviews,
        actual,
        # Adding the exclude of createdAt and lastEditedAt to unblock pipeline blocks due to UTC vs GMT string dates.
        # Ideally this will be fixed "properly"
        exclude_regex_paths=["\['trackHash'\]", "\['createdAt'\]", "\['lastEditedAt'\]"],
    )
