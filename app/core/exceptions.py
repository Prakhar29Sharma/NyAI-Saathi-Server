class QueryProcessingError(Exception):
    """Exception raised when query processing fails"""
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)