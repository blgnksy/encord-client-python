import datetime

from encord.orm.label_row import AnnotationTaskStatus, LabelRowMetadata, LabelStatus

FAKE_LABEL_ROW_METADATA = LabelRowMetadata(
    label_hash="",
    created_at=datetime.datetime.now(),
    last_edited_at=datetime.datetime.now(),
    data_hash="",
    data_title="",
    data_type="VIDEO",
    data_link="",
    dataset_hash="",
    dataset_title="",
    label_status=LabelStatus.NOT_LABELLED,
    annotation_task_status=AnnotationTaskStatus.QUEUED,
    is_shadow_data=False,
    duration=100,
    frames_per_second=25,
    number_of_frames=100 * 25,
    height=100,
    width=10,
)
