#
# This is a Shiny web application. You can run the application by clicking
# the 'Run App' button above.
#
# Find out more about building applications with Shiny here:
#
#    http://shiny.rstudio.com/
#

library(shiny)

data_df <- readRDS("data-df.rds")

# Define UI for application that draws a histogram
ui <- fluidPage(

    # Application title
    titlePanel("National Population Health Survey Findings - May 17, 2023"),

    # Sidebar with a slider input for number of bins
    sidebarLayout(
        sidebarPanel(
            sliderInput("bins",
                        "Number of bins (between 1 and 50)",
                        min = 1,
                        max = 50,
                        value = 30)
        ),

        # Show a plot of the generated distribution
        mainPanel(
            plotOutput("distPlot"),
            h2("Statistics (NPHS) Sample Table below"),
            dataTableOutput("hat_table")
        )
    )
)

# Define server logic required to draw a histogram
server <- function(input, output) {

    output$distPlot <- renderPlot({
        # generate bins based on input$bins from ui.R
        x    <- faithful[, 2]
        bins <- seq(min(x), max(x), length.out = input$bins + 1)

        # draw the histogram with the specified number of bins
        hist(x, breaks = bins, col = 'darkgray', border = 'white', xlab = 'Age when first experienced brain fog.')
    })
    output$mysessioninfo <- renderPrint({sessionInfo()})
    output$installed_pkgs <- renderPrint({names(installed.packages()[,"Package"])})
    output$hat_table <- renderDataTable(data_df)
}

# Run the application
shinyApp(ui = ui, server = server)
