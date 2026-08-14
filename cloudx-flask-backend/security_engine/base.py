from abc import ABC, abstractmethod


class SecurityEngineError(RuntimeError):
    """Base error for Cloud-X security-engine adapters."""


class SecurityEngineNotConfigured(SecurityEngineError):
    """Raised when an adapter capability has not been configured."""


class SecurityEngineUpstreamError(SecurityEngineError):
    """Raised when the configured security engine cannot satisfy a request."""

    def __init__(self, message, status_code=None):
        super().__init__(message)
        self.status_code = status_code


class SecurityEngine(ABC):
    """Cloud-X-owned domain contract implemented by security providers."""

    @abstractmethod
    def status(self):
        raise NotImplementedError

    @abstractmethod
    def overview(self):
        raise NotImplementedError

    @abstractmethod
    def agents(self, limit=100):
        raise NotImplementedError

    @abstractmethod
    def alerts(self, limit=50):
        raise NotImplementedError

    @abstractmethod
    def sca(self, agent_id, limit=100):
        raise NotImplementedError

    @abstractmethod
    def fim(self, agent_id, limit=100):
        raise NotImplementedError
