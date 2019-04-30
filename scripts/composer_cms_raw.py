import sys
sys.path.append("..")
import json

from DataManager.collector.dataset.generator import Composer
from DataManager.collector.dataset.stage import CMSRawStage
from DataManager.collector.dataset.resource import CMSResourceManager


if __name__ == "__main__":
    cms_resource_manager = CMSResourceManager(
        sys.argv[1], int(sys.argv[2]),
        resource=eval(sys.argv[3])
    )

    raw_stage = CMSRawStage(save_stage=True, source=cms_resource_manager)

    composer = Composer(
        dataset_name="CMS-RAW-Dataset",
        stages=[
            raw_stage
        ]
    )

    composer.compose(use_spark=True)
    composer.save()