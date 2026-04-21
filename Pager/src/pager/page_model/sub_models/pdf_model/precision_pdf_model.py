from ..base_sub_model import BaseSubModel
from typing import Dict
import subprocess
import json
import os
from pdf2image import convert_from_path

from dotenv import load_dotenv
load_dotenv(override=True)

NULL_PAGE = {
    "number": -1,
    "tables": [],
    "images": [],
    "width": None,
    "height": None,
    "words": []
}

class PrecisionPDFModel(BaseSubModel):
    def __init__(self) -> None:
        super().__init__()
        self.pdf_json: Dict
        self.count_page: int|None 
        # self.num_page: int = 0

    def from_dict(self, input_model_dict: Dict):
        self.pdf_json = input_model_dict

    def to_dict(self) -> Dict:
        return self.pdf_json
    

    def read_from_file(self, path_file: str, method: str = "w") -> None:
        self.path = path_file
        self.pdf_json = self.__read(path_file, method)
        self.count_page = len(self.pdf_json['pages']) if "pages" in self.pdf_json.keys() else 0

    def clean_model(self)-> None:
        self.pdf_json = {}
        self.count_page = None
        # self.num_page = 0

    def __read(self, path, method):
        # Путь к основному jar (например, /app/bin/precisionPDF.jar)
        jar_path = os.environ["JAR_PDF_PARSER"]
        
        # Получаем папку, где лежит основной jar
        jar_dir = os.path.dirname(jar_path)
        
        # Формируем пути к новым библиотекам
        core_jar = os.path.join(jar_dir, "jai-imageio-core-1.4.0.jar")
        j2k_jar = os.path.join(jar_dir, "jai-imageio-jpeg2000-1.4.0.jar")
        
        # Собираем Classpath. В Linux/Docker используется двоеточие ":"
        # Мы включаем основной JAR и обе библиотеки JAI
        classpath = f"{jar_path}:{core_jar}:{j2k_jar}"
        
        # Имя главного класса из вашего лога
        main_class = "DedocTableExtractor"
        
        # Формируем команду через Classpath
        comands = ["java", "-cp", classpath, main_class, "-i", path]
        
        if method == "w":
            comands.append("-w")
        elif method != "r":
            raise ValueError('Method "r" - rows or "w" - words')

        # Запуск
        res = subprocess.run(comands, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Логируем ошибки Java, если они есть
        if res.stderr:
            print("--- Java Stderr ---")
            print(res.stderr.decode("utf-8"))
            print("-------------------")

        if res.returncode != 0:
            print(f"Java process failed with return code {res.returncode}")
            return dict()

        try:
            stdout_str = res.stdout.decode("utf-8")
            if not stdout_str.strip():
                return dict()
                
            return json.loads(stdout_str)
        except json.JSONDecodeError as e:
            print(f"JSON Error: {e}")
            print(f"Raw output: <{stdout_str}>")
            return dict()

    def save_pdf_as_imgs(self, path_dir: str):
        for i, page in enumerate(self.pdf_json["pages"]):
            name_file = os.path.join(path_dir, f"page_{i}.png")
            w = int(page["width"])
            h = int(page["height"])
            img = convert_from_path(self.path, first_page=i+1, last_page=i+1, size=(w,h))[0]
            img.save(name_file)
