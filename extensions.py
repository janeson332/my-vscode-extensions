import subprocess
import argparse
import requests


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Downloads vscode Plugins")
    parser.add_argument("-i","--install",help="Installs the downloaded extensions",action="store_true")
    args = parser.parse_args()

    vsextensions = [
        "https://marketplace.visualstudio.com/_apis/public/gallery/publishers/CoenraadS/vsextensions/bracket-pair-colorizer-2/0.2.0/vspackage",
        "https://marketplace.visualstudio.com/_apis/public/gallery/publishers/ms-vscode/vsextensions/cpptools/1.1.1/vspackage",
        "https://marketplace.visualstudio.com/_apis/public/gallery/publishers/twxs/vsextensions/cmake/0.0.17/vspackage",
        "https://marketplace.visualstudio.com/_apis/public/gallery/publishers/ms-vscode/vsextensions/cmake-tools/1.5.2/vspackage",
        "https://marketplace.visualstudio.com/_apis/public/gallery/publishers/eamodio/vsextensions/gitlens/11.0.1/vspackage",
        "https://marketplace.visualstudio.com/_apis/public/gallery/publishers/ms-python/vsextensions/python/2020.11.358366026/vspackage",
        "https://marketplace.visualstudio.com/_apis/public/gallery/publishers/njpwerner/vsextensions/autodocstring/0.5.3/vspackage",
        "https://marketplace.visualstudio.com/_apis/public/gallery/publishers/VisualStudioExptTeam/vsextensions/vscodeintellicode/1.2.10/vspackage",
        "https://marketplace.visualstudio.com/_apis/public/gallery/publishers/vscode-icons-team/vsextensions/vscode-icons/11.0.0/vspackage"
    ]


    install_filenames = []

    for extension in vsextensions:
        print("Fetch from: {0}".format(extension))
        r = requests.get(extension,allow_redirects=True)
        if(r):
            if "content-type" in r.headers:
                if(r.headers["content-type"].find("application/vsix") >= 0):
                    #parse filename
                    filename = ""
                    if "Content-Disposition" in r.headers:
                        start_idx = r.headers["Content-Disposition"].find("filename=")
                        if(start_idx >=0):
                            filename = r.headers["Content-Disposition"][start_idx+len("filename="):r.headers["Content-Disposition"].find(";",start_idx)]
                    
                    if(filename != ""):
                        open(filename,"wb").write(r.content)
                        install_filenames.append(filename)
                                
                else:
                    print("Extension has wrong content type (has {0}".format(r.headers["content-type"]))
            else:
                print("Extension has no content-type, but neccessary")
        else:
            print("Could not fetch from current link...")

    if(args.install):
        for filename in install_filenames:
            process = subprocess.run(["code","--install-extension",filename])