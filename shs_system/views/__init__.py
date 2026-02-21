from .academic_year import *
from .auth import *
from .dashboard import *
from .form_manage import *
from .grading_average import *
from .manage_class import *
from .promotion_management import *
from .school_info import *
from .scores import *
from .student_management import *
from .subject_manage import *
from .teacher_management import *
from .teacher_remarks import *
from .user_management import *
from .views_report_cards import *
from .score_management import *
from .security import *

# Import all names from each view module to make them available when importing from views
__all__ = []

# Dynamically add all imported names to __all__
import sys

current_module = sys.modules[__name__]
__all__.extend([name for name in dir(current_module) if not name.startswith("_")])
