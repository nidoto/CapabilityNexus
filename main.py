from app import CapabilityNexusApp


def main():
    app = CapabilityNexusApp()

    print()
    print("CapabilityNexus Console Test")
    print("Type a UMI line (e.g. UMI_DATA motion.pitch=90), or 'Exit'")

    try:
        while True:
            line = input(">")

            if line == "Exit":
                break

            app.umi_parser.parse(line)
    except (EOFError, KeyboardInterrupt):
        pass

    app.close()


if __name__ == "__main__":
    main()
