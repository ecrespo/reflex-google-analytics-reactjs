import reflex as rx

config = rx.Config(
    app_name="google_analytics_reactjs_demo",
    show_built_with_reflex=False,
    plugins=[
        rx.plugins.RadixThemesPlugin(
            theme=rx.theme(appearance="light", accent_color="amber", gray_color="sand", radius="large"),
        ),
    ],
    disable_plugins=[rx.plugins.SitemapPlugin],
)
