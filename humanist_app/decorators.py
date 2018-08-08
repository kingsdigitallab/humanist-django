from django.shortcuts import redirect


def require_user(function):
    def wrap(request, *args, **kwargs):
        if request.user.is_authenticated:
            if request.user.is_active:
                return function(request, *args, **kwargs)
            else:
                return redirect('/Restricted/denied')
        else:
            return redirect('/Restricted/?next={}'.format(
                request.get_full_path()))

    wrap.__doc__ = function.__doc__
    wrap.__name__ = function.__name__
    return wrap


def require_editor(function):
    def wrap(request, *args, **kwargs):
        if request.user.is_authenticated:
            if request.user.is_staff:
                return function(request, *args, **kwargs)
            else:
                return redirect('/Restricted/denied')
        else:
            return redirect('/Restricted/?next={}'.format(
                request.get_full_path()))

    wrap.__doc__ = function.__doc__
    wrap.__name__ = function.__name__
    return wrap
