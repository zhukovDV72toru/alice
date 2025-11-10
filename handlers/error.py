from aliceio import F, Router
from aliceio.fsm.context import FSMContext
from aliceio.types import Message, Response

from fsm.states import PatientInfo

router = Router()

class ErrorHandlers:    
    async def handle_error(self, message: Message, state: FSMContext) -> Response:        
        return Response(
            text = f"Ничего не понял, повторите",
            tts = f"Ничего не понял, повторите"
            ) 

# Регистрация обработчиков
def setup_error_handlers(
    router: Router
):
    handlers = ErrorHandlers()
    
    router.message.register(
        handlers.handle_error
    )
