import json
import re
from math import isclose



# INPUT_JSONL = "C:/Users/howto/Downloads/SemanticSearch/RagTestProject/testing/mineru/MineruExtractedAnswers.jsonl"
# OUTPUT_JSONL = "C:/Users/howto/Downloads/SemanticSearch/RagTestProject/testing/mineru/ScoredMineru.jsonl"
# INPUT_JSONL = "C:/Users/howto/Downloads/SemanticSearch/RagTestProject/testing/pure_llm/PureLLMExtractedAnswers.jsonl"
# OUTPUT_JSONL = "C:/Users/howto/Downloads/SemanticSearch/RagTestProject/testing/pure_llm/ScoredPureLLM.jsonl"
# INPUT_JSONL = "C:/Users/howto/Downloads/SemanticSearch/RagTestProject/testing/pymupdf_full/PyMuPDFFullExtractedAnswers.jsonl"
# OUTPUT_JSONL = "C:/Users/howto/Downloads/SemanticSearch/RagTestProject/testing/pymupdf_full/ScoredPyMuPDFFull.jsonl"
# INPUT_JSONL = "C:/Users/howto/Downloads/SemanticSearch/RagTestProject/testing/pymupdf_partial/PyMuPDFPartialExtractedAnswers.jsonl"
# OUTPUT_JSONL = "C:/Users/howto/Downloads/SemanticSearch/RagTestProject/testing/pymupdf_partial/ScoredPyMuPDFPartial.jsonl"
INPUT_JSONL = "C:/Users/howto/Downloads/SemanticSearch/RagTestProject/testing/pager/PagerExtractedAnswers.jsonl"
OUTPUT_JSONL = "C:/Users/howto/Downloads/SemanticSearch/RagTestProject/testing/pager/ScoredPager.jsonl"

def load_jsonl(path):
    items = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                items.append(json.loads(line))
    return items

def levenshtein_distance(s1, s2):
    if len(s1) > len(s2):
        s1, s2 = s2, s1

    distances = range(len(s1) + 1)
    for i2, c2 in enumerate(s2):
        distances_ = [i2 + 1]
        for i1, c1 in enumerate(s1):
            if c1 == c2:
                distances_.append(distances[i1])
            else:
                distances_.append(1 + min((distances[i1], distances[i1 + 1], distances_[-1])))
        distances = distances_
    return distances[-1]


def anls_compute(groundtruth, prediction, threshold=0.5):
    dist = levenshtein_distance(groundtruth, prediction)
    length = max(len(groundtruth.upper()), len(prediction.upper()))
    value = 0.0 if length == 0 else float(dist) / float(length)
    anls = 1.0 - value
    if anls<=threshold:
        anls = 0.0
    return anls

def is_float_equal(reference, prediction, include_percentage: bool = False, is_close: float = False) -> bool:
    def get_precision(gt_ans: float) -> int:
        precision = 3
        if '.' in str(gt_ans):
            precision = len(str(gt_ans).split('.')[-1])
        return precision

    reference = float(str(reference).strip().rstrip("%").strip())
    try:
        prediction = float(str(prediction).strip().rstrip("%").strip())
    except:
        return False

    if include_percentage:
        gt_result = [reference / 100, reference, reference * 100]
    else:
        gt_result = [reference]
    for item in gt_result:
        try:
            if is_close:
                if isclose(item, prediction, rel_tol=0.01):
                    return True
            precision = max(min(get_precision(prediction), get_precision(item)), 2)
            if round(prediction, precision) == round(item, precision):
                return True
        except Exception:
            continue
    return False


def get_clean_string(s):
    s = str(s).lower().strip()
    s = s.replace(",", "")
    if s.endswith("kg"):
        s = s.rstrip("kg").strip()
    if s.endswith("mm"):
        s = s.rstrip("mm").strip()
    if s.endswith("m"):
        s = s.rstrip("m").strip()
    if s.endswith("meters"):
        s = s.rstrip("meters").strip()
    if s.endswith("acres"):
        s = s.rstrip("acres").strip()
    if s.endswith("minutes"):
        s = s.rstrip("minutes").strip()
    if s.endswith("mile"):
        s = s.rstrip("mile").strip()
    if s.endswith("miles"):
        s = s.rstrip("miles").strip()
    if s.endswith("million"):
        s = s.rstrip("million").strip()
    if s.endswith("thousand"):
        s = s.rstrip("thousand").strip()
    if s.endswith("billion"):
        s = s.rstrip("billion").strip()
    # remove parenthesis
    s = re.sub(r'\s*\([^)]*\)', '', s).strip()
    # remove quotes
    s = re.sub(r"^['\"]|['\"]$", "", s).strip()
    s = s.strip().lstrip("$").strip()
    s = s.strip().lstrip("£").strip()
    s = s.strip().rstrip("%").strip()
    return s

def is_exact_match(s):
    flag = False
    # Website
    if "https://" in s:
        flag = True
    # code file
    if s.endswith(".py") or s.endswith("ipynb"):
        flag = True
    if s.startswith("page"):
        flag = True
    # telephone number
    if re.fullmatch(r'\b\d+(-\d+|\s\d+)?\b', s):
        flag = True
    # time
    if "a.m." in s or "p.m." in s:
        flag = True
    # YYYY-MM-DD
    if re.fullmatch(r'\b\d{4}[-\s]\d{2}[-\s]\d{2}\b', s):
        flag = True
    # YYYY-MM
    if re.fullmatch(r'\b\d{4}[-\s]\d{2}\b', s):
        flag = True
    # Email address
    if re.fullmatch(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', s):
        flag = True
    return flag


def isfloat(num):
    try:
        float(num)
        return True
    except Exception as e:
        return False

def eval_score(gt, pred, answer_type):
    if answer_type=="Integer":
        try:
            gt = get_clean_string(str(gt))
            if len(re.findall(r"\d+,\s*\d+", gt, re.DOTALL)) > 0: # deal with Integer value formatted as "96,395"
                gt = "".join([_.strip() for _ in gt.split(",")])
            gt = int(gt)
        except:
            gt = gt
        try:
            pred = get_clean_string(str(pred))
            if len(re.findall(r"\d+,\s*\d+", pred, re.DOTALL)) > 0: # deal with Integer value formatted as "96,395"
                pred = "".join([_.strip() for _ in pred.split(",")])
            pred = int(pred)
        except:
            pred = ""
        score = (gt==pred)
    elif answer_type=="Float":
        gt = get_clean_string(str(gt))
        pred = get_clean_string(str(pred))
        
        if len(re.findall(r"\d+,\s*\d+", gt, re.DOTALL)) > 0: # deal with Integer value formatted as "96,395"
            gt = "".join([_.strip() for _ in gt.split(",")])
        try:
            gt = float(gt)
        except:
            gt = gt
        
        if len(re.findall(r"\d+,\s*\d+", pred, re.DOTALL)) > 0: # deal with Integer value formatted as "96,395"
            pred = "".join([_.strip() for _ in pred.split(",")])
        try:
            pred = float(pred)
        except:
            pred = str(pred)

        try:
            score = is_float_equal(gt, pred, include_percentage=True, is_close=True)
        except:
            score = 0

    elif answer_type in ["String", "None"]:
        gt = get_clean_string(gt)
        pred = get_clean_string(pred)
        if is_exact_match(gt):
            score = (gt==pred)
        else:
            score = anls_compute(gt, pred)
    else:
        if isinstance(gt, str) and gt.startswith("["):
            try:
                gt = eval(gt)
            except:
                gt = gt
        if not isinstance(gt, list):
            gt = [gt]
        if isinstance(pred, str) and pred.startswith("["):
            try:
                pred = eval(pred)
            except:
                pred = pred
        if not isinstance(pred, list):
            pred = [pred]
        if isinstance(pred, list) and len(pred) == 0:
            pred = [""]
        if isinstance(gt[0], dict):
            gt = ["-".join([str(value) for key,value in _.items()]) for _ in gt]
        if isinstance(pred[0], dict):
            pred = ["-".join([str(value) for key,value in _.items()]) for _ in pred]

        # print(len(gt), len(pred))
        # print(gt, pred)
        def cal_score_v3(gt, pred):
            gt = [get_clean_string(a) for a in gt]
            pred = [get_clean_string(a) for a in pred]
            if isfloat(gt[0]) or is_exact_match(gt[0]):
                score_v3 = ("-".join(gt)=="-".join(pred))
            else:
                greedy_scores = [max([anls_compute(str(gt_v), str(pred_v)) for pred_v in pred]) for gt_v in gt]
                score_v3 = sum(greedy_scores) / len(gt) * min(1, len(gt) / len(pred)) ** 0.5
            return score_v3

        score_v3 = cal_score_v3(gt, pred)

    score_v3 = score if answer_type in ["Integer", "Float", "String", "None"] else score_v3

    return float(score_v3)


def main():
    rows = load_jsonl(INPUT_JSONL)

    total_scores = 0
    for row in rows:
        predicted_concise_answer = row.get("predicted_concise_answer")
        if predicted_concise_answer == "Fail to extract":
            score_v3 = 0.0
        else:
            try:
                predicted_concise_answer_eval = eval(predicted_concise_answer) if not isinstance(eval(predicted_concise_answer), set) else list(eval(predicted_concise_answer))
            except:
                predicted_concise_answer_eval = predicted_concise_answer

            answer_format = row.get("answer_format")
            answer = row.get("answer")
            print("Evaluating question " + row.get("question_id"))
            score_v3 = eval_score(answer, predicted_concise_answer_eval, answer_format)

        total_scores += score_v3
        row.setdefault("score_v3", score_v3)

    generalized_score = total_scores / len(rows)

    print("score is " + str(generalized_score))


    with open(OUTPUT_JSONL, "w", encoding="utf-8") as out_f:
        for row in rows:
            out_f.write(json.dumps(row, ensure_ascii=False) + "\n")

if __name__ == "__main__":
    main()


