class BaseError(Exception):
    """ 
        Chained Exception used a basis for all errors.
        The cause should be a String or an Exception object 
        
        Attributes: 
            message: a string containing the error message
            cause: The cause of the exception. Must be an object that can be
                converted to a string
    """

    def __init__(self, message, cause):
        self.message = message
        self.cause = cause

    def __str__(self):
        return self.__print_cause__()

    def __repr__(self):
        return self.__print_cause__()

    def __print_cause__(self):
        if self.cause == None:
            return self.message
        return "%s. Caused by: %s" % (self.message, str(self.cause))

class ValidationError(BaseError):
    """
        A class representing a Validation Error
    """
    def __print_cause__(self):
        return "Validation Error: " + super().__print_cause__()

class DataError(BaseError):
    """
        A class representing a Financial Data error
    """
    def __print_cause__(self):
        return "Data Error: " + super().__print_cause__()


class CalculationError(BaseError):
    """
        A class representing a calculation error
    """
    def __print_cause__(self):
        return "Calculation Error: " + super().__print_cause__()

class ReportError(BaseError):
    """
        A class representing a calculation error
    """
    def __print_cause__(self):
        return "Report Error: " + super().__print_cause__()

class FileSystemError(BaseError):
    """
        A class representing a flesystem error
    """
    def __print_cause__(self):
        return "Filesystem Error: " + super().__print_cause__()

class AWSError(BaseError):
    """
        A class representing an AWS error
    """
    def __print_cause__(self):
        return "AWS Error: " + super().__print_cause__()

    def resource_not_found(self):
        '''
            Returns true if the exception was caused by a resource that
            was not found.
        '''
        return "(404)" in str(self.cause) and "NOT FOUND" in str(self.cause).upper()
    

    