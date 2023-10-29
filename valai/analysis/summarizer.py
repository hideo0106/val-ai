# valai/analysis/summarizer.py

import random
import logging
from ..llamaflow import FlowEngine

logger = logging.getLogger(__name__)

ANALYZE_LOGIC = ['Observation', 'Insight', 'Theory', 'Fact', 'Concept', 'Topic', 'Subject', 'Theme',
                 'Idea', 'Point', 'Argument', 'Conclusion', 'Summary', 'Analysis', 'Opinion', 'Perspective',
                 'Viewpoint', 'View', 'Position', 'Standpoint', 'Stand', 'Take', 'Thought', 'Notion',
                 'Belief', 'Impression', 'Judgment', 'Assessment', 'Appraisal', 'Estimation', 'Evaluation',
                 'Appreciation', 'Critique', 'Criticism', 'Comment', 'Observation', 'Remark', 'Statement',
                 'Reflection', 'Thought', 'View', 'Opinion', 'Comment', 'Note', 'Point', 'Idea', 'Impression']

IMPROVE_LOGIC = ['The article', 'The summary', 'Missing from', 'Importantly', 'Insightfully', 'Factually',
                 'Succinctly', 'To rephrase', 'To summarize', 'To conclude', 'Replacing', 'Changing', 'Adding']

def paragraph_length(s_length : int) -> str:
    if s_length > 200:
        return 'long'
    elif s_length < 100:
        return 'short'
    else:
        return 'medium'

# This is a chain of density (https://arxiv.org/pdf/2309.04269.pdf) implementation for content summaraization
# Chain of Density is a method of content summarization that uses a large language model to
# read data into context and then return a summary of the information therein, iteratively
# improving the summary by identifying missing information and then adding that information
# We enhance this algorithm by performing an analysis of the article before summarizing it
# and adding character persona enhancements

class ChainOfAnalysis:
    """
    """
    def __init__(self, engine : FlowEngine):
        self.engine = engine
        self.iteration = 0
        self.summaries = []
        self.information_idx = 1
        self.information = []
        self.last_data = ''
        self.last_analysis = ''

    def analyze(self, article : str, observations : int = 5, o_length : int = 512, o_temp : float = 0.7, **kwargs):
        """Analyze the article and return the analysis"""
        prompt = f"""
### System: You are Val, my creative AI assistant.  You have a masters degree Journalism.  Your job is as my reporter, and we need to get all the facts!  You follow instructions and requests to be my heplful assistant.  Thanks so much for your help!
### Instruction: We are summarizing an article.  We will first *Analyze* the article, then develop a *Summary*, then determine *Missing Information*, and then *Resummarize*.  Follow each *Request* as it is provided.
### *Article*:
```article
{article}
```
### *Request*: Given *Article*, analyze the purpose of this article, output the results as *Analysis*.  Our analysis is detailed and accurate, spanning all of the topics that are covered in the article.
### *Analysis* the most significant topics in the article are (with commentary):
"""

        #logger.debug(f"Summarizing with prompt: {prompt}")
        self.engine.feed(prompt=prompt)
        logger.info(f"Analyzing ({self.engine.n_past})")
        logic = []
        generated = []
        for n in range(observations):
            if len(logic) == 0:
                logic = ANALYZE_LOGIC.copy()
            topic = random.choice(logic)
            logic.remove(topic)
            o_prompt = f"- {topic} {n}:"
            self.engine.feed(prompt=o_prompt)
            generated += o_prompt
            generated += self.engine.read(max_tokens=o_length, abort_tokens=['|', '`'], stop_tokens=['\n'],
                                          n_temp=o_temp, **kwargs)
        self.analysis = ''.join(generated)
        return ''.join(generated)

    def summarize(self, paragraphs : int = 2, s_length : int = 512, s_temp : float = 0.2, **kwargs) -> list[str]:
        """Summarize the article and return the summary"""
        prompt = f"""```
### *Request*: Given *Article* and *Analysis*, output *Summary* which contains a summary of *Article*.  Our summary is detailed, erudite, succinty, and accurate.
### *Summary* (erudite and informative; {paragraphs} paragraphs):
```summary"""

        self.engine.feed(prompt=prompt)
        logger.info(f"Summarizing ({self.engine.n_past})")
        generated = []
        for p in range(paragraphs):
            prompt = f"\n## Paragraph {p} ({paragraph_length(s_length)})\n"
            self.engine.feed(prompt=prompt)
            information = self.engine.read(max_tokens=s_length, stop_tokens=['\n'], abort_tokens=['`'],
                                          n_temp=s_temp, **kwargs)
            generated.append(''.join(information))
        return generated

    def improve(self, theories : int = 5, t_length : int = 512, t_temp : float = 1.0, **kwargs):
        """Improve the summary by identifying missing information"""
        prompt = "```\n"
        if self.iteration == 0:
            prompt += """### *Format* Samples of missing information:
- Information #: Insightfully, the summary could be improved by doing this.
- Information #: Conceptually, this is very important to the article, the summary should include it.
- Information #: Factually, the summary is missing a concise fact that was in the article.
- Information #: Observantly, I should change a part of the summary from this one to something that would improve the summary.
"""

        prompt += f"""### *Request*: Given the *Article*, as an expert and a professional, determine missing information from the *Summary*, output the results as *Missing Information* using the specified *Information Format*.
### *Missing Information* ({theories} entries, novel information not contained in the summary):
"""

        logger.debug(f"Improving with prompt: {prompt}")
        self.engine.feed(prompt=prompt)
        logger.info(f"Theorizing ({self.engine.n_past})")
        generated = []
        logic = []
        for n in range(theories):
            if len(logic) == 0:
                logic = IMPROVE_LOGIC.copy()
            topic = random.choice(logic)
            logic.remove(topic)
            prompt = f"- Information {self.information_idx}: {topic}"
            generated.append(prompt)
            self.engine.feed(prompt=prompt)
            information = self.engine.read(max_tokens=t_length, stop_tokens=['\n'],
                                          n_temp=t_temp, **kwargs)
            generated += information
            self.information.append(''.join(information))
            self.information_idx += 1
        return ''.join(generated)

    def resummarize(self, paragraphs : int = 2, s_length : int = 512, s_temp : float = 0.2, **kwargs) -> list[str]:
        """Resummarize the article and return the summary"""
        prompt = f"""

### *Request*: Using any summary and Information, output a new, longer, improved new *Summary* {self.iteration + 1} that includes our *Summary* {self.iteration} and any Information.
### *Directive*: Paragraph length is constrained.  Missing periods at the end of sentences should be added.
### *Format* paragraph score results: 
### Paragraph Score #: paragraph ended abruptly - MEDIUM
### Paragraph Score #: paragraph is incorrect - LOW
### Paragraph Score #: no errors found - HIGH
### Improved *Summary* {self.iteration + 1} (including information, reorganized, erudite, and expanded; {paragraphs} paragraphs):
```summary"""

        logger.debug(f"Resummarizing with prompt: {prompt}")
        self.engine.feed(prompt=prompt)
        logger.info(f"Resummarizing ({self.engine.n_past})")
        generated = []
        for p in range(paragraphs):
            prompt = f"\n## Paragraph {p} ({paragraph_length(s_length)})\n"
            self.engine.feed(prompt=prompt)
            information = self.engine.read(max_tokens=s_length, stop_tokens=['\n'], abort_tokens=['`'],
                                          n_temp=s_temp, **kwargs)
            generated.append(''.join(information))
        return generated

    def reset_context(self, summary : list[str], **kwargs):
        """Reset the context of the summarizer, using the last summary as the new context"""
        self.iteration = 0
        self.information_idx = 1
        prompt = f"""
### System: You are Val, my creative AI assistant.  You have a masters degree in English, and are an expert researcher.  You are my copy editor, and your job is to fix our errors and any missing periods.  You follow instructions and requests to be my heplful assistant.  Thanks so much for your help!
### Instruction: We are summarizing an article.  We will first develop a *Summary*, then *Missing Information*, and then *Resummarize*.  Follow each *Request* as it is provided.
### *Article*:
```article
{self.last_data}
```
### *Request*: Given *Article*, output *Summary 0* which contains a summary of *Article*.  Our summary is detailed, erudite, succinty, and accurate; Our summary is one, two, or three paragraphs.
### *Format* paragraph score results:
### Paragraph Score #: paragraph ended abruptly - MEDIUM
### Paragraph Score #: paragraph is incorrect - LOW
### Paragraph Score #: no errors found - HIGH
### *Summary*:
```summary"""
        self.engine.reset(**kwargs)
        self.engine.feed(prompt=prompt, **kwargs)
        for i, s in enumerate(summary, 1):
            summary_prompt = f"\n{s}\n### Paragraph Score {i}:"
            if len(s) < 50:
                self.engine.feed(prompt=summary_prompt + " Paragraph too short - LOW")
            else:
                self.engine.feed(prompt=summary_prompt, **kwargs)
                self.engine.read(max_tokens=15, stop_tokens=['\n'], abort_tokens=['`'], n_temp=1.2, **kwargs)
    
    def __call__(self, data, iterations : int = 3, constrain_data : int = 10000, **kwargs):
        """Summarize an article and return the summary"""
        logger.info("Chain of Analysis Agent invoked")
        self.iteration = 0
        self.information_idx = 1
        data = data[:constrain_data]
        self.last_data = data
        analysis = self.analyze(data, **kwargs)
        self.last_analysis = analysis
        summary = self.summarize(**kwargs)
        if len(summary) == 0:
            logger.warn("Summary is empty, retrying")
            summary = self.__call__(data, **kwargs)
        else:
            self.summaries = [summary]
            logger.debug(f"Summary: {summary}")
            self.reset_context(summary, **kwargs)
            for _ in range(iterations):
                theories = self.improve(**kwargs)
                logger.debug(f"Theories: {theories}")
                summary = self.resummarize(**kwargs)
                logger.debug(f"Updated Summary: {summary}")
                self.iteration += 1
                self.summaries.append(summary)
                self.reset_context(summary, **kwargs)
                logger.debug(f"Scored Results")
        return '\n'.join(summary)

    @classmethod
    def from_config(cls, **kwargs):
        """Create a new instance of ChainOfAnalysis"""
        engine = FlowEngine.from_config(**kwargs)
        cod = cls(engine=engine)
        return cod

if __name__ == '__main__':
    from ..scrape import fetch_url

    logging.basicConfig(level=logging.DEBUG)
    config = {
        'model_path': '/mnt/biggy/ai/llama/gguf/',
        #'model_file': 'mistral-7b-phibrarian-32k.Q8_0.gguf',
        #'model_file': 'mistral-7b-sciphi-32k.Q8_0.gguf',
        'model_file': 'zephyr-7b-beta.Q8_0.gguf',
        'n_ctx': 2 ** 15,
        'n_batch': 512,
        'n_gpu_layers': 14,
        #'url': 'https://www.forbes.com/sites/jemimamcevoy/2022/10/13/alex-jones-likely-doesnt-have-1-billion-he-does-own-five-homes-in-texas-though',
        #'url': 'https://stackoverflow.com/questions/16981921/relative-imports-in-python-3'
        #'url': 'https://bionexuskc.org/bionexus-kc-announces-kc-region-tech-hub-designation-for-biologics-and-manufacturing-proposal/',
        #'url': 'https://www.kctv5.com/2023/10/24/kansas-city-region-designated-tech-hub-us-dept-commerce/',
        #'url': 'https://news.uchicago.edu/how-bioelectricity-could-regrow-limbs-and-organs'
        'url': 'https://theeyewall.com/trying-to-make-sense-of-why-otis-exploded-en-route-to-acapulco-this-week/'
    }
    
    cod = ChainOfAnalysis.from_config(**config)
    data = fetch_url(**config)
    summary = cod(data=data, **config)

    print(f"""
Article Summary Chain:

""")
    for i, s in enumerate(cod.summaries):
        print(s)
    print(f"""Final Summary: {summary}""")
