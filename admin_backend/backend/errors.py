class ApiError(Exception):
    def __init__(self, message, status_code=400, code='api_error', payload=None):
        super().__init__(message)
        self.message = str(message)
        self.status_code = int(status_code)
        self.code = code
        self.payload = payload or {}

    def to_dict(self):
        data = {'error': self.message}
        if self.code:
            data['code'] = self.code
        data.update(self.payload)
        return data


class BadRequestError(ApiError):
    def __init__(self, message, code='bad_request', payload=None):
        super().__init__(message, status_code=400, code=code, payload=payload)


class NotFoundError(ApiError):
    def __init__(self, message, code='not_found', payload=None):
        super().__init__(message, status_code=404, code=code, payload=payload)


class ConflictError(ApiError):
    def __init__(self, message, code='conflict', payload=None):
        super().__init__(message, status_code=409, code=code, payload=payload)


class ServiceUnavailableError(ApiError):
    def __init__(self, message, code='service_unavailable', payload=None):
        super().__init__(message, status_code=503, code=code, payload=payload)
