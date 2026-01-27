from environments.base import BaseConfig


# Development environment configuration
class Config(BaseConfig):
    env = "dev" # TODO[SB]: make more foolproof
    rbacConfig = {
        "owners": ["sil_mstr.nl#EXT#@silasmstr.onmicrosoft.com",
                   "silas_mstr.nl#EXT#@silasmstr.onmicrosoft.com",
                   "nigel_mstr.nl#EXT#@silasmstr.onmicrosoft.com",
                   "tom_mstr.nl#EXT#@silasmstr.onmicrosoft.com"
                   ],
        "contributors": [],
        "readers": []
    }

