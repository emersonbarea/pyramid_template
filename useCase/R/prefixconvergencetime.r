
rm(list = ls())
library(ggplot2)

df <- read.csv('/home/tocha/Documentos/projetos/MiniSecBGP/useCase/logs/prefixconvergencetime.csv')

df$testes <- factor(df$teste, labels = c("1","2"))

mean_rg <- mean(df$media)

mean_rg


p <- ggplot(df, aes(x = testes, y = tempo)) +  
  geom_violin() +
  geom_hline(yintercept = mean_rg, linetype = "dashed")

p <- p + 
  scale_x_discrete(name="Número do teste") + 
  scale_y_continuous(limits=c(0,10), breaks=seq(0,10,2), expand = c(0, 0), name="Tempo [s]")

p + theme(text = element_text(size=25.5))

