import reflex as rx

config = rx.Config(
    app_name="mapcn_demo",
    plugins=[
        rx.plugins.SitemapPlugin(),
        rx.plugins.RadixThemesPlugin(
            theme=rx.theme(
                appearance="inherit",
                accent_color="blue",
                gray_color="slate",
                radius="medium",
            ),
        ),
    ],
)
