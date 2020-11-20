import argparse
import logging
import os
import subprocess
import sys
import time
from abc import ABC, abstractmethod
from typing import List

import requests


class Extension(object):
    def __init__(self,marketplace_link:str,publisher:str=None, name:str=None,version:str=None):
        self.name = ""
        self.publisher = ""
        self.version = ""
        self.marketplace_link = ""

        if((publisher != None) and (name != None) and (version != None) and 
           (publisher != "") and (name != "") and (version != "")):
            self.name = name
            self.publisher = publisher
            self.version = version
            self.marketplace_link = "https://marketplace.visualstudio.com/_apis/public/gallery/publishers/{0}/vsextensions/{1}/{2}/vspackage".format(self.publisher,self.name,self.version)
        elif(marketplace_link != None):
            if(self._extract_from_link(marketplace_link) != None):
                raise ValueError("given link is not a valid marketplace link...")

            self.marketplace_link = marketplace_link.rstrip("\r\n ").strip(" \r\n")
        else:
            raise ValueError("No arguments given")

    def _extract_from_link(self,link:str):
        
        prefix = "https://marketplace.visualstudio.com/_apis/public/gallery/publishers/"

        if(link.find(prefix)< 0):
            return -1
        sub = link[link.find(prefix)+len(prefix):]
        
        pos = sub.find("/")
        if(pos < 0):
            return -1
        self.publisher = sub[0:pos]
        pos = sub.find("vsextensions/")
        if(pos < 0):
            return -1
        sub = sub[pos+1+len("vsextension/"):]
        pos = sub.find("/")
        if(pos < 0):
            return -1
        self.name = sub[0:pos]
        sub = sub[pos+1:]
        pos = sub.find("/")
        if(pos < 0):
            return -1
        self.version = sub[0:pos]

        if(sub[pos:].find("vspackage") < 0):
            return -1
    def __eq__(self, rhs):
        return ((self.name == rhs.name) and (self.version == rhs.version) and (self.publisher == rhs.publisher))
    def __ne__(self, rhs):
        return not(self.__eq__(rhs))
    def __hash__(self):
        return self.__str__().__hash__()
    def __str__(self):
        return "{0}.{1}-{2}".format(self.publisher,self.name,self.version)

class ExtensionReader(ABC):
    def __init__(self):
        super().__init__()

    @abstractmethod
    def get_extensions(self)->List[Extension]:
        pass

class FileExtensionReader(ExtensionReader):
    def __init__(self,filename:str):
        super().__init__()
        self.filename = filename
        if(not(os.path.isfile(self.filename))):
            raise RuntimeError("Error, extensions file does not exist..")


    def get_extensions(self):
        extensions = []
        with open(self.filename) as f:
            for line in f:
                try:
                    if(line.strip("\r\n ").rstrip("\r\n ") != ""):
                        extensions.append(Extension(line))
                except ValueError as err:
                    logging.warning("{0} is not a valid marketplace link".format(line))

        return extensions
    


class VsCodeExtensionReader(ExtensionReader):
    def __init__(self):
        super().__init__()
        self._cmd = ["code", "--list-extensions", "--show-versions"]

    def get_extensions(self):
        extensions = []

        proc = subprocess.run(self._cmd,capture_output=True)
        if(proc.returncode == 0):
            entries = proc.stdout.decode().split("\n")
            for entry in entries:
                try:
                    extensions.append(self._parse(entry))
                except:
                    pass

        return extensions

    def _parse(self,entry:str)->Extension:
        publ = entry[0:entry.find(".")]
        name = entry[entry.find(".")+1:entry.rfind("@")]
        version = entry[entry.find("@")+1:]

        return Extension(None,publ,name,version)

class PathExtensionReader(ExtensionReader):
    def __init__(self,path:str):
        super().__init__()
        if(os.path.isdir(path)):
            self.path = path
        

    def get_extensions(self):
        extensions = []

        for file in os.listdir(self.path):
            if file.endswith(".vsix"):
                extensions.append(self._parse(file[0:0-len(".vsix")]))

        return extensions

    def _parse(self,entry:str)->Extension:
        publ = entry[0:entry.find(".")]
        entry = entry[entry.find(".")+1:]
        version = entry[entry.rfind("-")+1:]
        name = entry[:entry.rfind("-")]
        
        return Extension(None,publ,name,version)


class ExtensionWriter(object):
    def __init__(self,filename:str="my_extensions.txt"):
        self.filename = filename

    def write(self,extensions:List[Extension]):
        with open(self.filename,"w") as f:
            for ext in extensions:
                f.write(ext.marketplace_link + "\n")

class ExtensionDownloader(object):
    def __init__(self,path:str = "./"):
        self._path = path
        if(not(os.path.isdir(self._path))):
            raise ValueError("given path is not valid ..")

    def download(self,extensions:List[Extension]):
        if(extensions == None):
            return
        
        for ext in extensions:
            self._download(ext)
        
    def _download(self,ext:Extension):
        logging.info("Try to download {0}".format(ext))
        sys.stdout.write("Downloading {0}\n".format(str(ext)+".vsix"))
        r = requests.get(ext.marketplace_link,allow_redirects=True)
        if(r.status_code == 200):
            # check if correct header (if its really a vsix file)
            if(("content-type" in r.headers) and (r.headers["content-type"].find("application/vsix")>=0)):
                #check for filename from the http header and compare with own filename (if not the same)
                #the api may changed or something other bad happened ..
                if(("Content-Disposition" in r.headers) and (r.headers["Content-Disposition"].find("filename=") >= 0)):
                    pos = r.headers["Content-Disposition"].find("filename=")
                    filename = r.headers["Content-Disposition"][pos+len("filename="):r.headers["Content-Disposition"].find(";",pos)]

                    if(filename != (str(ext)+".vsix")):
                        logging.error("Some inconsistent filename on: {0} -(fetched) and {1} -(local)".format(filename,str(ext)+".vsix"))
                        return
                    else:
                        with open(os.path.join(self._path,filename),"w+b") as f:
                            f.write(bytearray(r.content))
                            

            else:
                logging.warning("content type of {0} not in *.vsix".format(ext.marketplace_link))
        elif(r.status_code == 429):
            #status code when microsoft blocks the request (spammed the downloads too often)
            logging.warning("Spammed downloads too frequenly, Microsoft blocked the request..")
            logging.warning("Block will stop at: {0}".format(time.ctime(int(r.headers["X-RateLimit-Reset"]))))
        else:
            logging.warning("could not fetch {0} from {1}\n http status code:{2} \n with content: \n{3}".format(ext,ext.marketplace_link,r.status_code,r.content))
            logging.debug(r.content)
            logging.debug(r.headers)
            return



def check_dir_create(dir:str):
    if(not(os.path.isdir(dir))):
        try:
            os.makedirs(dir)
        except FileExistsError:
            pass
        except:
            sys.stderr.write("error on creating the directory: {0}".format(dir))
            sys.exit(1)
            

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Downloads vscode Plugins",formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("-i","--install",help="install the extension from the download dir, if not installed yet",action="store_true")
    parser.add_argument("--download-dir",help="download directory",default="./download")
    parser.add_argument("-d","--download",help="download the extensions, if not done yet",action="store_true")
    parser.add_argument("--extensions-file",help="name of file of the  marketplacelinks (used for reading and storing)",default="my-extensions.txt")
    parser.add_argument("-w","--write-extensions-file",help="writes extensionsfile of current installed extensions",action="store_true")
    
    if(len(sys.argv)==1):
        parser.print_help()
        sys.exit(1)
    args = parser.parse_args()
    
    if(args.download):
        check_dir_create(args.download_dir)
        try:
            file_extensions = FileExtensionReader(args.extensions_file).get_extensions()
            path_extensions = PathExtensionReader(args.download_dir).get_extensions()
            extensions = set(file_extensions)-set(path_extensions)
            ExtensionDownloader(args.download_dir).download(extensions)

        except Exception as err:
            sys.stderr.write(err)
            sys.exit(1)

    if(args.install):
        check_dir_create(args.download_dir)
        try:
            extensions = PathExtensionReader(args.download_dir).get_extensions()
            for ext in extensions:
                process = subprocess.run(["code","--install-extension",os.path.join(args.download_dir,str(ext)+".vsix")])
                if(process.returncode != 0):
                    sys.stderr("Error on installing extension: {0}\n".format(ext))

        except Exception as err:
            sys.stderr.write(err)
            sys.exit(1)

    if(args.write_extensions_file):
        try:
            vscode_extensions = VsCodeExtensionReader().get_extensions()
            ExtensionWriter(args.extensions_file).write(vscode_extensions)
            sys.stdout.write("Extensions file written as: {0}\n".format(args.extensions_file))
        except Exception as err:
            sys.stderr.write(err)
            sys.exit(1)
