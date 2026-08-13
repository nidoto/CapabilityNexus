import os
import json



class PackageManager:


    def __init__(
        self,
        registry
    ):

        self.packages = {}

        self.registry = registry



    def load(
        self,
        path
    ):


        for name in os.listdir(path):


            package_path = os.path.join(
                path,
                name
            )


            if not os.path.isdir(
                package_path
            ):

                continue



            manifest_file = os.path.join(
                package_path,
                "manifest.json"
            )


            capability_file = os.path.join(
                package_path,
                "capabilities.json"
            )



            if not os.path.exists(
                manifest_file
            ):

                continue



            if not os.path.exists(
                capability_file
            ):

                continue



            #
            # Load Manifest
            #

            with open(
                manifest_file,
                "r",
                encoding="utf-8"
            ) as f:

                manifest = json.load(f)



            #
            # Load Capabilities
            #

            with open(
                capability_file,
                "r",
                encoding="utf-8"
            ) as f:

                capabilities = json.load(f)



            #
            # Save Package
            #

            self.packages[name] = {

                "manifest": manifest,

                "capabilities": capabilities

            }



            #
            # Register Capability
            #

            for capability in capabilities.get(
                "capabilities",
                []
            ):


                self.registry.register(

                    manifest["name"],

                    capability

                )



            print(

                "[Package]",

                manifest["name"]

            )