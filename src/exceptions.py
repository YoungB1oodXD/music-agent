from __future__ import annotations


class MusicAgentException(Exception):
    """Base exception for Music Agent"""

    pass


class AuthenticationError(MusicAgentException):
    """Raised when authentication fails"""

    pass


class TokenExpiredError(MusicAgentException):
    """Raised when token has expired"""

    pass


class UserNotFoundError(MusicAgentException):
    """Raised when user is not found"""

    pass


class PlaylistNotFoundError(MusicAgentException):
    """Raised when playlist is not found"""

    pass


class PlaylistAccessDeniedError(MusicAgentException):
    """Raised when user doesn't have access to playlist"""

    pass


class TrackNotFoundError(MusicAgentException):
    """Raised when track is not found"""

    pass


class TrackAlreadyExistsError(MusicAgentException):
    """Raised when track already exists in playlist"""

    pass


class RecommendationError(MusicAgentException):
    """Raised when recommendation generation fails"""

    pass


class SemanticSearchError(MusicAgentException):
    """Raised when semantic search fails"""

    pass


class CFRecommendError(MusicAgentException):
    """Raised when collaborative filtering fails"""

    pass


class LLMError(MusicAgentException):
    """Raised when LLM call fails"""

    pass


class SessionNotFoundError(MusicAgentException):
    """Raised when session is not found"""

    pass


class ValidationError(MusicAgentException):
    """Raised when input validation fails"""

    pass
