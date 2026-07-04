def route(mode):

    mode = mode.lower()

    if mode == "student":
        return "student"

    elif mode == "professor":
        return "professor"

    else:
        return "invalid"


if __name__ == "__main__":

    print(route("student"))
    print(route("professor"))
    print(route("abc"))