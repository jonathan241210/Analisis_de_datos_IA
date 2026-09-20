class AppError(Exception):
    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


MSG_PLOT_CLEAN = "Limpia el dataset primero y vuelve a intentar el gráfico."
MSG_DB_CONNECT_SOON = (
    "La conexión a base de datos se habilitará cuando confirmemos motor y host."
)
