# -*- coding: utf-8 -*-


def log(message):
    text = str(message)
    print(text)
    try:
        CLMainForm.WritePythonLog("[sum_wall_weight.py] " + text)
    except Exception:
        try:
            CLMainForm.WriteLog("[sum_wall_weight.py] " + text)
        except Exception:
            pass


def safe(label, fn):
    try:
        value = fn()
        log(label + ": " + str(value))
        return value
    except Exception as ex:
        log(label + " ERROR: " + str(ex))
        return None


def normalize_name(text):
    if text is None:
        return ""
    return str(text).strip().lower()


def get_member(obj, *names):
    for name in names:
        try:
            value = getattr(obj, name)
            if value is not None:
                return value
        except Exception:
            pass
    return None


def to_float(value):
    if value is None:
        return None

    text = str(value).strip()
    if not text:
        return None

    text = text.replace("\u00a0", "").replace(" ", "").replace(",", ".")

    try:
        return float(text)
    except Exception:
        return None


def weight_tokens():
    return (
        "вес",
        "масса",
        "масса кг",
        "вес кг",
        "weight",
        "mass",
        "net weight",
        "gross weight",
        "mass kg",
        "kg",
        "кг",
    )


def is_weight_like(name, caption):
    tokens = weight_tokens()
    return any(token in name or token in caption for token in tokens)


def extract_weight_from_parameter(parameter):
    name = normalize_name(get_member(parameter, "name", "Name"))
    caption = normalize_name(get_member(parameter, "caption", "Caption"))
    value = get_member(parameter, "value", "Value", "val", "Val", "text", "Text")

    if not is_weight_like(name, caption):
        return None

    return to_float(value)


def dump_parameter_names(obj, limit=50):
    try:
        params = Library.GetObjectParameters(obj.idObject)
    except Exception as ex:
        log("parameter dump ERROR: " + str(ex))
        return

    rows = []
    for parameter in params:
        name = str(get_member(parameter, "name", "Name"))
        caption = str(get_member(parameter, "caption", "Caption"))
        value = get_member(parameter, "value", "Value", "val", "Val", "text", "Text")
        rows.append((name, caption, value))

    for i, item in enumerate(rows[:limit]):
        log("param[{0}] name={1}; caption={2}; value={3}".format(i, item[0], item[1], item[2]))


def dump_weight_candidates(obj):
    try:
        params = Library.GetObjectParameters(obj.idObject)
    except Exception as ex:
        log("candidate dump ERROR: " + str(ex))
        return

    for parameter in params:
        name = normalize_name(get_member(parameter, "name", "Name"))
        caption = normalize_name(get_member(parameter, "caption", "Caption"))
        value = get_member(parameter, "value", "Value", "val", "Val", "text", "Text")

        if is_weight_like(name, caption):
            raw = get_member(parameter, "Value", "value", "val", "Val", "Text", "text")
            log(
                "candidate name={0}; caption={1}; value={2}; raw={3}".format(
                    name,
                    caption,
                    value,
                    raw
                )
            )


def get_wall_objects():
    part_type_id = safe("PART_TYPE id", lambda: Library.GetParamDefId("PART_TYPE"))
    if part_type_id is None:
        raise Exception("Could not resolve PART_TYPE id")

    walls = safe("Wall objects", lambda: Library.GetObjectParametersByValues(part_type_id, "Стена", True, ';'))
    if walls is None:
        raise Exception("Could not get walls by PART_TYPE")

    return walls


log("=== SUM WALL WEIGHT start ===")

walls = get_wall_objects()
wall_count = safe("Wall count", lambda: walls.Count)
if wall_count is None:
    raise Exception("Could not count wall objects.")

total_weight = 0.0
found_count = 0
missing_count = 0
diagnostic_limit = 5
dump_limit = 2

for index, obj in enumerate(walls):
    if index < diagnostic_limit:
        log("wall[{0}] idObject={1}; name={2}".format(index, obj.idObject, obj.Name))

    wall_weight = None
    try:
        for parameter in Library.GetObjectParameters(obj.idObject):
            wall_weight = extract_weight_from_parameter(parameter)
            if wall_weight is not None:
                break
    except Exception as ex:
        log("wall[{0}] parameter scan ERROR: {1}".format(index, ex))

    if index < dump_limit:
        dump_weight_candidates(obj)

    if wall_weight is None:
        missing_count += 1
        if index < diagnostic_limit:
            dump_parameter_names(obj, 25)
        continue

    found_count += 1
    total_weight += wall_weight
    if index < diagnostic_limit:
        log("wall[{0}] weight={1}".format(index, wall_weight))

log("Wall count: " + str(wall_count))
log("Weight found for: " + str(found_count))
log("Weight missing for: " + str(missing_count))
log("Total wall weight: " + str(total_weight))
log("=== SUM WALL WEIGHT end ===")
