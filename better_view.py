import asyncio
from datetime import datetime, timedelta
from nextcord import ui, Interaction
from threading import Timer
from typing import Optional

# the amount of seconds before the interaction becomes invalid
# made for securing the edit of that message, should be higher than 0.
MERCY_SECONDS: int = 30


# this is an abstract class that can be inherited to make a view
# that disables itself after a certain amount of time
# before you cannot respond to an interaction anymore or when timeout has been reached.
class AutoDisableView(ui.View):
    interaction: Optional[Interaction] = None
    message_id: Optional[int] = None
    _timer: Optional[Timer] = None

    def init_interaction(
            self,
            interaction: Interaction,
            message_id: Optional[int] = None,
            start_timer: bool = True
    ) -> None:
        '''
        Initializes the interaction and message_id attributes.
        This is required for the view to work properly.

        Parameters
        ----------
        interaction: Interaction
            The interaction that the view is attached to.
            Needs to be the interaction that currently was received and is being processed.
        message_id: Optional[int]
            The message id of the message if the response is a followup.
        start_timer: bool
            Whether to start the timer that will disable the view
            after the timeout has been reached. Defaults to True.'''

        self.interaction = interaction
        self.__stopped: asyncio.Future[bool] = interaction.client.loop.create_future()
        self.message_id = message_id
        if start_timer:
            self.disable_message_start_timer()

    def disable_message_start_timer(self, interaction: Optional[Interaction] = None) -> None:
        '''
        Starts the timer that will disable the message after the timeout has been reached.
        This is called automatically when init_interaction() is called with `start_timer` set to True.'''
        seconds = (
                          self.interaction.created_at  # dont rely on expires_at because it may not have responded
                          + timedelta(minutes=15)  # interaction is valid for 15 minutes in case of message being sent
                          - datetime.utcnow().replace(tzinfo=self.interaction.expires_at.tzinfo)
                  ).total_seconds() - MERCY_SECONDS
        if self._timer:
            self._timer.cancel()
        self._timer = Timer(seconds, self._disable_message_task)
        self._timer.start()
        if interaction:
            # if you responded with defer or edit_message, you can pass the interaction to this method
            # to extend the timer to the new interaction
            self.init_interaction(interaction, self.message_id, False)

    # override
    def stop(self) -> None:
        self._disable_message_task()
        super().stop()

    # override
    def _dispatch_timeout(self) -> None:
        if self.__stopped.done():
            return
        self.interaction.client.loop.create_task(self._disable_view_on_timeout(),
                                                 name=f"discord-ui-disable-view-timeout-{self.id}")
        super()._dispatch_timeout()

    def _disable_message_task(self) -> None:
        self.interaction.client.loop.create_task(self._disable_message_buttons())

    def _disable_children(self) -> None:
        for child in self.children:
            child.disabled = True

    async def _disable_message_buttons(self) -> None:
        self._disable_children()
        if self.message_id:
            await self.interaction.followup.edit_message(self.message_id, view=self)
        else:
            await self.interaction.edit_original_message(view=self)
        self._timer.cancel()

    async def _disable_view_on_timeout(self) -> None:
        await self._disable_message_buttons()
