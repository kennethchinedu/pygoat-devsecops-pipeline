import login 

def concat_then_raw(request):
    name = request.POST.get("name")
    q = "SELECT * FROM t WHERE user='" + name + "'"
    # ruleid: django-raw-sql-from-request
    login.objects.raw(q)


def concat_inside_raw(request):
    name = request.POST.get("name")
    # ruleid: django-raw-sql-from-request
    login.objects.raw("SELECT * FROM t WHERE user='" + name + "'")


def fstring_raw(request):
    name = request.POST.get("name")
    # ruleid: django-raw-sql-from-request
    login.objects.raw(f"SELECT * FROM t WHERE user='{name}'")


def subscript_source(request):
    name = request.POST["name"]
    q = "SELECT * FROM t WHERE user='" + name + "'"
    # ruleid: django-raw-sql-from-request
    login.objects.raw(q)


def parameterised(request):
    name = request.POST.get("name")
    # ok: django-raw-sql-from-request
    login.objects.raw("SELECT * FROM t WHERE user=%s", [name])


def orm_filter(request):
    name = request.POST.get("name")
    # ok: django-raw-sql-from-request
    login.objects.filter(user=name)


def constant_query(request):
    # ok: django-raw-sql-from-request
    login.objects.raw("SELECT * FROM t")


def body_source(request):
    q = "SELECT * FROM t WHERE user='" + request.body.decode() + "'"
    # ruleid: django-raw-sql-from-request
    login.objects.raw(q)
