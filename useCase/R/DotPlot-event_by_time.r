library(ggplot2)

cty_mpg <- aggregate(mpg$cty, by=list(mpg$manufacturer), FUN=mean)

cty_mpg

mtcars